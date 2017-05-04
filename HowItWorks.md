# How it all works

The Atomic Tracer package is set up to be language agnostic. You won't need to edit any of the core plugin's code to extend it.

## Folder Structure

All code for the supported languages can be found in `lib/langs/`. For example, to get the tracer to work with Python, I created a `python/` directory there with three files:

- info.yml
- parse.py
- inject.py

The package searches all folders under the `langs/` directory. All 3 files must be present for this to be considered a valid language extension. The parse and inject scripts should be written in the language you're adding support for (technically they _could_ be written in any language but it makes sense to write them in the target language).

Here's what each file is supposed to do:

### info.yml

A simple configuration file. Here's a sample:

```YAML
languageName: Python #Just for reference
fileExtension: .py
runCommand: python [file]
```
The `fileExtension` is how the plugin knows to activate the correct scripts for the given file. The `runCommand` is used to run the `parse` and `inject` scripts below (where `[file]` is replaced with the filepath).

### parse.py

The parse script is where most of the functionality is. Its job is to find where a variable is declared and its scope. It is run when you select a variable to trace in the editor, and it is given these arguments on stdin:

`filepath variable_name line_number`

The `filepath` is just the path to the current file in the editor. The `variable_name` is whatever variable was selected. And `line_number` is where in the code it was selected to be traced.

This script should then output a JSON string to stdout with this information:

`{scope:{start:<number>,end:<number>},decl:{line:<number>}}`

Where the `start` and `end` mark the complete scope the variable exists in. So this would be the start and end line of a function the variable was declared in, for example. The line the variable was declared in should be given in `line`.

If there is any error that the script can catch, it should be returned as a JSON string as well:

`{error:<string>}`

Things you may want to account for are syntax errors in the original code, or just trying to search for a variable that doesn't exist. But fear not! Any error caused in your script will be returned to the user in the interface. It would just help to give more useful messages when something common occurs.

### inject.py

The inject script is responsible for actually tracing the variable once its scope and declaration info has been determined. It does this by injecting print statements and capturing the output after running the modified file. It is run after the parse script, assuming that happened successfully. It is given:

 `filepath variable_name scope_info`

 The first two arguments are the same as before. `scope_info` is a base64 serialized JSON string. So your code will have to decode from base64, and then parse the JSON. This will be whatever output your parse script prints out.

 It is expected to output a JSON array:

 `[{line:<number>,output:<string>},...]`

With the output of each line and what line it was coming from. Check the Python folder for an example of how this is accomplished. The most straightforward way is simply to inject these print statements, and either save, run and delete a temporary file, or just evaluate the modified code without saving it. Either way, make sure to grab the line number this output is coming from (by making it output the value of the variable as well as its line number)

## Making your own

Hopefully that should give you enough information to create an extension to trace your favorite language! I've only tested this with Python, but I'd love to see this being used for all sorts of languages. If you feel like this system doesn't work very well with a compiled language, or with different versions of Python, or if the `runCommand` should be more customizable, please feel free to suggest it or fork and make a pull request!

Any feedback is appreciated!
