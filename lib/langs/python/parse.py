# The parse script expects on stdin:
#   filepath variable_name line_number
# And is expected to output on stdout:
#   {scope:{start:<num>,end:<num>},decl:{line:<num>}}
# If there is a syntax error in running the given file, it should return the error as:
#   {error:[error_string]}

# Any error thrown while running this script will be returned to the user in the UI.

import json
import sys,symtable
import ast
import ntpath

#Some helper functions
def path_leaf(path):
    #from http://stackoverflow.com/a/8384788/1278023
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)

#Grab the arguments from stdin
filepath,variable_name,line_number = "","",""
if(len(sys.argv) == 4):
    filepath = sys.argv[1]
    variable_name = sys.argv[2]
    line_number = int(sys.argv[3])
else:
    raise ValueError("Incorrect number of arguments! Parse script takes exactly three arguments: filepath variable_name line_number")

#We create our ASTWalker class to find all variables with the given name
#As well as mark the start and end scopes of functions and for loops
class ASTWalker(ast.NodeVisitor):
    varList = []#Keep track of the variables in this tree
    forLoops = {}#for loops are indexed by their line number
    functions = {}#Functions are indexed by their names
    classes = {}
    def grabVar(self,node):
        #This grabs variables from assignment statements, for loops, and function args
        if(type(node) == ast.Attribute):#Skip collecting attributes to keep things simple
            return
        if(node.id != variable_name):#No need to collect variables that don't have the name we're looking for
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
        #Iterator variables don't get picked up in the Assign nodes, so we have to find them by looking at for loops
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
    def visit_ClassDef(self, node):
        classStart = node.lineno
        classEnd = node.body[len(node.body)-1].lineno
        self.classes[node.name] = {'start':classStart,'end':classEnd}

        ast.NodeVisitor.generic_visit(self, node)

def Parse():
    #Read the file
    fileObj = open(filepath)
    fileContent = fileObj.read()
    fileObj.close()
    #Get the AST
    try:
        tree = ast.parse(fileContent) #This also checks that there's no syntax error in the original code
    except:
        print(json.dumps({'error':sys.exc_info()[0]}))
        return;

    #Now we can run our ASTWalker on our AST to grab all this info
    walker = ASTWalker()
    walker.visit(tree)

    if(len(walker.varList) == 0):
        print(json.dumps({'error':"Variable '" + variable_name + "' not found."}))
        return;

    #Since python has no concept of a "variable declaration" that's distinct from
    # just an assignment, since the same variable name can exist in multiple scopes,
    # we need to do some extra work to figure where our variable is
    globalTable = symtable.symtable(fileContent,path_leaf(filepath),"exec")

    def getTableEnd(table):
        if(table.get_type() == "module"):
            #Table end is the end of the file
            return len(fileContent.split("\n"))
        if(table.get_type() == "function"):
            return walker.functions[table.get_name()]['end']
        if(table.get_type() == "class"):
            return walker.classes[table.get_name()]['end']


    def getScope(varObj,table):
        #This function will use the symbol tables to figure out which scope this variable
        # exists in
        for childTable in table.get_children():
            try:
                childTable.lookup(varObj['name'])
                tableStart = childTable.get_lineno()
                tableEnd = getTableEnd(childTable)
                if(varObj['line'] >= tableStart and varObj['line'] <= tableEnd):
                    table = getScope(childTable,childTable)
            except KeyError:
                pass

        return table;

    candidates = {}
    tables = []
    for var in walker.varList:
        scopeTable = getScope(var,globalTable)
        start = var['line']
        end = getTableEnd(scopeTable)
        if(line_number >= start and line_number <= end):
            if(not scopeTable in candidates):
                candidates[scopeTable] = []
                tables.append(scopeTable)
            candidates[scopeTable].append(var)

    closest = tables[0]
    if(len(tables) > 1):
        #Get the table whose start is closest one before line_number
        for t in tables:
            if(line_number - t.get_lineno() < line_number - closest.get_lineno()):
                closest = t
    #The first one in the list is the first assignment, therefore the declaration
    finalVarObj = candidates[closest][0];

    scopeData = {'scope':{
                    'start':closest.get_lineno(),
                    'end':getTableEnd(closest)
                    },
                'decl':{'line':finalVarObj['line']}
                }
    print(json.dumps(scopeData))

#Initiate everything
Parse()
