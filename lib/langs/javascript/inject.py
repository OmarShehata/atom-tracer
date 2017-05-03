# PLACEHOLDER FILE FOR FUTURE JAVASCRIPT CODE. USE FOR REFERENCE

# The inject script expects on stdin (scopeInfo is what is returned by the parse script):
#   filepath variable_name scopeInfo
# And is expected to output on stdout:
#   [{line:<num>,output:<num>},...]

import json
import sys,symtable
import ast
import base64
import os
from subprocess import Popen, PIPE

#Helper functions
def getTabs(line):
    #Gets the tabs/spaces at the beginning of a line
    trimmed = line.strip()
    index = line.find(trimmed)
    return line[0:index]

#Grab the arguments from stdin
filepath,variable_name,line_number = "","",""
if(len(sys.argv) == 4):
    filepath = sys.argv[1]
    variable_name = sys.argv[2]
    jsonString = base64.b64decode(sys.argv[3]).decode('ascii')
    scopeInfo = json.loads(jsonString)
else:
    raise ValueError("Incorrect number of arguments! Parse script takes exactly three arguments: filepath variable_name line_number")

def Inject():
    #Read the file
    fileObj = open(filepath)
    fileContent = fileObj.read()
    fileObj.close()
    #Split by lines
    lines = fileContent.split("\n")
    start = scopeInfo['decl']['line'] #Start at the var declaration and end at the end of the scope
    end = scopeInfo['scope']['end']
    statement = "print(\'{\"atomic_tracer\":true,\"line\":<line>,\"output\":\"\'+str(" + variable_name + ")+\'\"}\')"
    #Inject print statements
    for i in range(start,end):
        lineNum = i+1
        #Skip lines that end with ':' or empty lines
        if(lines[i].find(":") > -1 or lines[i] == ""):
            continue
        stmt = statement.replace("<line>",str(lineNum))
        lines[i] += "\n" + getTabs(lines[i]) + stmt
        i += 1

    #Write code to temp file
    tempFile = filepath.replace(".py","-temp.py")
    fileObj = open(tempFile,"w")
    fileObj.write("\n".join(lines))
    fileObj.close()

    #Run file and get output
    process = Popen(["python", tempFile], stdout=PIPE)
    (output, err) = process.communicate()
    exit_code = process.wait()
    if(err):
        os.remove(tempFile)
        raise ValueError(err.decode('utf-8'))

    output = output.decode('utf-8')
    #Parse output (only get the output that we injected)
    lines = output.split("\n")
    cleanOutput = []
    for line in lines:
        try:
            out = json.loads(line)
            if('atomic_tracer' in out):
                cleanOutput.append(out)
        except:
            pass

    #Delete file
    os.remove(tempFile)

    print(json.dumps(cleanOutput))

Inject()
