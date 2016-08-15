# Given a filepath, a variable name & a line number where it was found
# return the line number it was declared in and its scope
# Also grabs function arguments and iterator variables
import sys
import ast,symtable
import os
import json

#Abstract Syntax Tree classes for visiting the nodes we need
class ASTWalker(ast.NodeVisitor):
    varList = []#Keep track of the variables in this tree
    forLoops = {}#for loops are indexed by their line number
    functions = {}#Functions are indexed by their names
    def grabVar(self,node):
        #Handle attributes??
        if(type(node) == ast.Attribute):
            return
        varObj = {'name':node.id,'line':node.lineno,'col':node.col_offset,'is_arg':False}
        self.varList.append(varObj)
    def visit_Assign(self, node):
        for target in node.targets:
            if(isinstance(target,ast.Tuple)):#this is to handle variables declared on the same line
                for el in target.elts:
                    self.grabVar(el)
            else:
                self.grabVar(target)
        ast.NodeVisitor.generic_visit(self, node)#Make sure to run the original method so the AST module can do its thing
    def visit_For(self,node):
        #Iterator variables don't get picked up in the Assign nodes, so we have to find them manually
        self.grabVar(node.target)
        #We also keep track of where this for loop starts and ends
        self.forLoops[node.lineno] = {'start':node.lineno,'end':node.body[len(node.body)-1].lineno,'is_arg':False}
        ast.NodeVisitor.generic_visit(self, node)
    def visit_FunctionDef(self,node):
        funcStart = node.lineno
        funcEnd = node.body[len(node.body)-1].lineno
        self.functions[node.name] = {'start':funcStart,'end':funcEnd}
        #Grab the arguments
        argList = node.args.args
        for argNode in argList:
            argName = argNode.arg
            varObj = {'name':argName,'line':node.lineno,'start':node.lineno,'col':-1,'end':funcEnd,'is_arg':True}
            self.varList.append(varObj)
        ast.NodeVisitor.generic_visit(self, node)


def getScope(symbolTable,varName):
    #Finds the start of the scope of this variable and its type (module, function, or class)
    # by iterating through the symbol table and its children
    #Returns an array of symbol tables for this variable name
    def checkTable(sTable,vName):
        #print(sTable)
        try:
            #If lookup is sucessful, this is the correct scope!
            sTable.lookup(vName)
            #But keep searching in case a variable with the same name exists in a different scope
            #childrenArray = []
            #for table in sTable.get_children():
            #    childrenArray = childrenArray + checkTable(table,varName)
            #return [sTable] + childrenArray
            return sTable
        except KeyError:
            #Otherwise, check its children
            for table in sTable.get_children():
                t = checkTable(table,vName)
                if(t != None):
                    return t
            #Nothing found? This variable doesn't exist!
            return None
    return checkTable(symbolTable,varName)

def parseFile(filename,varName,line):
    #The line number has to be given since the variable 'foo' may exist as globally or inside of a function
    #in order to know which one to trace, we need to be given where it was found so we can limit our search to that scope
    #If line number is omitted, it will default to 1

    #Read the file contents
    fileObj = open(filename)
    fileContent = fileObj.read()
    fileObj.close()
    #Grab the abstract syntax tree
    tree = ast.parse(fileContent)
    #Find the variable
    walker = ASTWalker()
    walker.visit(tree)
    varObj = None
    varsMatching = []#Collect all declarations, then grab the earliest one (by line number)
    for v in walker.varList:
        if(v['name'] == varName):
            varsMatching.append(v)
    def getKey(var):
        return var['line']
    varsMatching = sorted(varsMatching,key=getKey)
    varObj = varsMatching[0]
    #The symbol table tells us information about scope
    symbolTable = symtable.symtable(fileContent,filename,"exec")
    scopeTable = getScope(symbolTable,varName)
    #print(scopeTable)

    #return "invalid"

    if(len(varsMatching) == 0):#Variable was not found
        print("invalid")
        return "invalid"
    # Calculate the scope of this variable
    # The rule is, the scope always begins when it is declared
    # and ends whenever its symbol table ends
    fileLines = fileContent.split("\n")
    declLine = varObj['line']
    endLine = 0;
    scopeType = scopeTable.get_type()#module, class or function
    scopeName = scopeTable.get_name()

    if(scopeName == "top"):
        #Visible until end of file
        endLine = len(fileLines)
    else:
        if(scopeType == "function"):
            if(varObj['is_arg']):
                endLine = varObj['end']
            else:
                endLine = walker.functions[scopeName]['end']
        if(scopeType == "class"):
            #Not yet grabbing classes
            pass
        if(scopeType == "module"):
            #Not yet grabbing modules
            pass
    #Package everything to return
    newVarObj = {
        'name':varObj['name'],
        'scope':{
            'start':declLine,
            'end':endLine
        },
        'decl':{
            'line':varObj['line'],
            'col':varObj['col']
        }
    }
    print(json.dumps(newVarObj))
    return newVarObj;



if(len(sys.argv) < 3):
    print("Missing arguments: required filepath and variable name")
else:
    #if(3 in sys)
    parseFile(sys.argv[1],sys.argv[2],0)
