child_process = require('child_process')
fs = require('fs')
Path = require('path')
YAML = require('yamljs')
{CompositeDisposable} = require 'atom'
DismissableErrors = true

###
Atomic Tracer
-------------
In order to be flexible enough to support any language, this atom plugin
is little more than a UI. It mainly handles passing in user selections
to the relevant scripts, and displays them in the editor. It looks for these
language scripts inside lib/langs/

Every language should have a "parse" and an "inject" script, as well as an
info.yml file.

**parse**: [filepath variable_name line_number]
Takes in these arguments (line_number is the line at which this variable was
found, which may or may not be the same line where it was declared) and prints
a json string to stdout in this format:

{scope:{start:[num],end:[num]},decl:{line:[num]}}

If there is a compilation error with the error, it should return:

{error:[error_string]}

**inject**: [filepath variable_name scope]
Takes in these arguments (scope is what is returned above) and injects print/cout
statements every line into a new copy. Runs that copy, deletes that file, and captures
the output, parses it into stdout and prints it out. (Can also just edit the same file if necessary)
The output should look like this:

[{line:[num],output:[str]},...]

**info.yml**:
This has some meta data about the language, such as which filetypes to look for,
the name of that language.

###

module.exports = AtomTracer =
  resultArray:[],#An array of the Ink boxes displaying the output in the editor
  parseScripts:{},#A mapping of the file extensions and the parsing/injecting scripts

  activate: (state) ->
    moduleRef = @
    #Register the command
    @disposables  = new CompositeDisposable
    @disposables.add atom.commands.add "atom-text-editor", "atom-tracer:traceCommand": => @traceCommand()
    @disposables.add atom.workspace.observeTextEditors (editor) =>
      # Holding alt and double clicking on a variable name to select is how you initiate the trace
      view = atom.views.getView(editor)

      view.addEventListener('dblclick', () ->
          if moduleRef.altDown == true then  moduleRef.traceCommand() else moduleRef.clearResults()
      )
      view.addEventListener 'blur', (event) ->
        #Fix so that when we alt tab out and back, alt starts as false
        moduleRef.altDown = false
      view.addEventListener 'keydown', (event) ->
        if event.keyCode == 18 then moduleRef.altDown = true
      view.addEventListener 'keyup', (event) ->
        if event.keyCode == 18 then moduleRef.altDown = false
    #read the lib/langs folder and collect all the info
    languageDirectory =  Path.join(__dirname,"langs")
    fs.readdir languageDirectory, (err, folders) ->
      for folder in folders
        #Get the yaml config
        infoPath = Path.join(__dirname,"langs",folder,"info.yml")
        infoData = YAML.parse(fs.readFileSync(infoPath, {encoding:'utf-8'}))
        if(!infoData) #Failed to parse
          continue
        parseData = {language:infoData.languageName,runCommand:infoData.runCommand}
        #Get the parse file
        parsePath = Path.join(__dirname,"langs",folder,"parse"+infoData.fileExtension)
        if !fs.lstatSync(parsePath).isFile()
          atom.notifications.addError("Missing config file." ,{detail:"Found language '" + folder + "' but could not find parse file. Expected: " + parsePath})
        parseData['parseScript'] = parsePath
        #Get the inject file
        injectPath = Path.join(__dirname,"langs",folder,"inject"+infoData.fileExtension)
        if !fs.lstatSync(parsePath).isFile()
          atom.notifications.addError("Missing config file." ,{detail:"Found language '" + folder + "' but could not find inject file. Expected: " + injectPath})
        parseData['injectScript'] = injectPath

        if('parseScript' of parseData && 'injectScript' of parseData)
          moduleRef.parseScripts[infoData.fileExtension] = parseData
          console.log(moduleRef.parseScripts)


  deactivate: ->
    @disposables.dispose()

  consumeInk: (ink) ->
    #Grab ink from Atom's Services API
    @ink = ink

  createResult: (text,line) ->
    #Creates an ink result view and injects it at that line in the current editor
    el = document.createElement("span"); el.innerHTML = text
    editor = atom.workspace.getActiveTextEditor();
    line = line - 1;
    result = new @ink.Result(editor, [line,line],{content:el,type:'inline'})
    @resultArray.push(result)
    #Copy content to clipboard when the user clicks
    el.addEventListener 'click', (e) ->
      #Strip out the code tags
      text = text.replace("<code>","")
      text = text.replace("</code>","")
      atom.clipboard.write(text)
      atom.notifications.addSuccess("Copied to clipboard!")

  clearResults: () ->
    #Remove all the results
    r.remove() for r in @resultArray
    @resultArray = []

  #This is the core of the plugin. Calls the right scripts to trace this variable
  # and display the output
  trace: (varName,line) ->
    moduleRef = @
    #Get the filetype and check if this filetype is in our supported types
    editor = atom.workspace.getActiveTextEditor()
    fileType  = Path.extname(editor.buffer.file.path)
    filePath = editor.buffer.file.path
    if !(fileType of @parseScripts)
      atom.notifications.addError("Unimplemented filetype", {dismissable:DismissableErrors,detail:"There is no parser currently implemented for " + fileType + " files.\nVisit our github page to see if anybody is working on one, \nor make one yourself!"})
      return

    parseData = @parseScripts[fileType]
    #If found, please call the parse script to check if it's a real variable
    command = parseData.runCommand.replace("[file]",parseData.parseScript) + " \"" + filePath + "\" " + varName + " " + line
    child_process.exec(command, (error, stdout, stderr) ->
      #If all good, send the scope info the inject
      if(error || stderr)
        atom.notifications.addError("Failed to parse!", {dismissable:DismissableErrors,detail:error || stderr})
        return
      #Try to parse stdout as json
      try
          scopeInfo = JSON.parse(stdout)
          if 'error' of scopeInfo
              atom.notifications.addError("Parse script error!", {dismissable:DismissableErrors,detail:scopeInfo['error']})
              return
      catch error
        atom.notifications.addError("Error parsing JSON output from parse script!", {dismissable:DismissableErrors,detail:error})
        return

      #Run the inject script if no error
      command = parseData.runCommand.replace("[file]",parseData.injectScript) + " \"" + filePath + "\" " + varName + " " + btoa(JSON.stringify(scopeInfo))
      child_process.exec(command, (error, stdout, stderr ) ->
        if(error || stderr)
          atom.notifications.addError("Injection failed!", {dismissable:DismissableErrors,detail: error || stderr})
          return
        #Try to parse the output
        try
          traceData = JSON.parse(stdout)
          #Show where the variable was declared
          moduleRef.createResult("<code>`"+varName + "` declared here.</code>",scopeInfo.decl.line)
          #Collapse output into lines
          lineMap = {}
          for out in traceData
            if(lineMap[out.line])
              #Combine output
              lineMap[out.line].output += ", " + out.output
            else
              lineMap[out.line] = out
          #Show final results
          for key,out of lineMap
            moduleRef.createResult("<code>"+varName + " = "+out.output+"</code>",out.line)
        catch error
          atom.notifications.addError("Error parsing JSON output from inject script!", {dismissable:DismissableErrors,detail:error})
          return
        )

      )


  traceCommand: ->
    #Clear any previous results
    @clearResults()
    #Trace whatever is currently selected
    editor = atom.workspace.getActiveTextEditor();
    line = editor.getSelectedBufferRange().start.row+1
    @trace(editor.getSelectedText(),line)
