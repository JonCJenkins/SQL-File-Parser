import sys
import os
import json
import re
import textwrap
import locale
import io

def guess_encoding(file):
    #Pass a file and it will return the type of encoding to use, as .sql files are encoded and can be in multiple ways.
    with io.open(file, "rb") as f:
        data = f.read(5)
        
    if data.startswith(b"\xEF\xBB\xBF"):
        return "utf-8-sig"
    elif data.startswith(b"\xFF\xFE") or data.startswith(b"\xFE\xFF"):
        return "utf-16"
    else:
        try:
            with io.open(file, encoding="utf-8") as f:
                return "utf-8"
        except:
            return locale.getdefaultlocale()[1]

def create_query_string(sql_file):
    #Takes a file and will parse it out into one giant string.
    #Uses guess_encoding to find the proper encoding to use to decode the file.
    with open(sql_file, 'r', encoding=guess_encoding(sql_file)) as f_in:
        lines = f_in.read()  
        query_string = textwrap.dedent("""{}""".format(lines))
        return query_string

def getLines(filedir):
    #Turn sql file location into list of strings, containing each line
    #Removing any commented out blocks or lines
    sql = create_query_string(filedir)

    sql = re.sub(re.compile(r"/\*.*?\*/",re.DOTALL),"",sql)#Replaces all text between comment lines with empty string.
    
    lines = []
    line = ""

    #Splits up long string into lines, going character by character adding to the line string.
    #When a \n is found that line is appended and we begin a new line.
    #We skip tabs.
    for i in range(len(sql)):
        if sql[i] == '\n':
            lines.append(line)
            line = ""
        elif sql[i] == '\t':
            continue
        else:
            line = line + sql[i]

    #This removes all lines that start with --, which is a comment in sql.
    lines = [x for x in lines if not x.startswith("--")]

    return lines

def makeDic(series, dic):
    #Recursive function to convert a list into repeating dict:value pairs.
    #[one, two, three] -> {one:{two:{three:"Value"}}}
    if len(series) == 2:
        dic[series[0]] = series[1]
        return dic
    
    if series[0] not in dic:
        dic[series[0]] = {}
        
    dic[series[0]] = makeDic(series[1:], dic[series[0]])

    return dic

def findJoins(filedir, name, other, tabdict, simple, neato, conn, edges):
    #Performs a secondary parse of the sql file, looking for select statements within objects.
    #When they are found, we look for a join statement. If we find one, we assume all the tables
    #we find within that select statement are somewhat correlated, and draw connections between
    #them in a graphviz undirected graph. We display this to user and save it to disk. It can in
    #future be converted to a networkx graph easily to allow for graphical analysis to be performed.
    
    lines = getLines(filedir)

    #The current list of regular expressions used to match tables. Needs to be expanded to account for all
    #possible ways a table can be referenced in sql.
    regex = [r'(?<!\S)\w+\.\w+(?!\S)',#one.two
             r'(?<!\S)\w+\.\w+\.\w+(?!\S)',#one.two.three
             r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',#[one].[two]
             r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',#[one].[two].[three]
             r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',]#[one].[two].[three].[four]

    #list of colors used to color the graph created.
    colors = ["red", "blue", "green", "yellow", "orange", "purple", "black", "brown", "cyan",
              "pink", "magenta", "black", "chartreuse", "coral", "crimson", "chocolate", "indigo",
              "fuchsia", "lime", "maroon", "olive", "navy", "teal", "yellowgreen", "rosybrown", "orangered", "orchid", "tomato"]
    col = 0

    currobj = ""
    objs = []

    from graphviz import Graph

    #Graph object that holds our graph.
    dot = Graph(name+".T", strict=True)

    #Iterate through all of the lines of the sql file, looking for create statements for each of the objects we are looking for.
    for i in range(len(lines)):
        matchV = re.match(r'\s*CREATE\s+VIEW\s+(\[.+\]).(\[.+\])\s',lines[i],re.I)
        matchF = re.match(r'\s*CREATE\s+FUNCTION\s+(\[.+\]).(\[.+\])\s',lines[i],re.I)
        matchP = re.match(r'\s*CREATE\s+PROC\s+(\[.+\]).(\[.+\])\s',lines[i],re.I)
        matchT = re.match(r'\s*CREATE\s+TRIGGER\s+(\[.+\]).(\[.+\])\s',lines[i],re.I)

        if matchV or matchF or matchP or matchT:
            #When we find a match, record the name of the object so we can later know what object is creating these joins.
            if matchV:
                currobj = matchV.group(1)+'.'+matchV.group(2)
            elif matchP:
                currobj = matchP.group(1)+'.'+matchP.group(2)
            elif matchF:
                currobj = matchF.group(1)+'.'+matchF.group(2)
            elif matchT:
                currobj = matchT.group(1)+'.'+matchT.group(2)

            #Handle selecting a color for this object.
            if currobj not in objs:
                objs.append(currobj)
                col = objs.index(currobj) % len(colors)
            else:
                col = objs.index(currobj) % len(colors)

            #Look through all the lines in the declaration of this object.
            for line in range(i+1,len(lines)):
                #Look for select
                select = re.search(r'select',lines[line],re.I)
                
                if select:
                    #We want to see if this select contains a join, and always record all table references we find.

                    joins = False#Records if there is a join in this select statement
                    tables = []#Holds all the tables within this select statement

                    #Look through all the lines in this select.
                    for sel in range(line,len(lines)):

                        #Check every table regex against each line we find.
                        for r in regex:
                            table = re.findall(r, lines[sel])
                            tables = tables + table

                        join = re.search(r'join',lines[sel],re.I)

                        #if we find a join, we want to record this set of tables.
                        if join:
                            joins = True

                        where = re.search(r'where', lines[sel], re.I)

                        #Finish checking for a select statement, as we dont want to check too far.
                        if where or lines[sel].startswith("GO") or lines[sel].startswith("\n"):
                            #If there were joins, we can now record these tables on the graph.
                            if joins:
                                #All tables in tables[] should be interconnected

                                #But first we need to remove all of the aliases

                                tab = []

                                #Look through the list of tables we have collected for this select statement.
                                for f in range(len(tables)):
                                    #Split it up into each of the words that make it up, as in, "[one].[two]" becomes ["one","two"]
                                    s = re.findall(r'\[(.+?)\]', tables[f], re.I)

                                    if not s:
                                        s = re.split(r'\.', tables[f], re.I)

                                    #Other is the list of valid databases, and this will exclude aliases.
                                    if s[0] in other.keys() or s[1] in other.keys():
                                        #We want to skip over certain two ways that are the first two parts of a three way table name
                                        #We have a current object in s, and the next object that was found in temp.
                                        #We do this by looking to the next object and doing the same conversion as earlier to it.
                                        #Because of the way the regex works, it will be [one].[two] in s, and [one].[two].[three] in temp if it is a three way.
                                        #Thus, if one=one, two=two, and temp has three parts, we can be sure that this current s should be excluded in favor of
                                        #the three way it is a incomplete part of.
                                        threeway = False
                                        for k in range(len(tables)):
                                            temp = re.findall(r'\[(.+?)\]', tables[k], re.I)

                                            if not temp:
                                                temp = re.split(r'\.', tables[k], re.I)

                                            if temp[0] == s[0] and temp[1] == s[1] and len(temp) > 2:
                                                threeway = True
                                                break

                                        if threeway:
                                            continue

                                        #Now we simply need to convert this ["one","two"] format back into a single string (with no brackets)
                                        #Simple means we limit it to tables that were found by the findTables function.
                                        #If simple is not true then we simply need to do the conversion for all the tables we found
                                        #(This will often also include some views that were referenced like tables in joins, which can be good or bad,
                                        #which is why this is a user option of whether or not they want a simplified table.)
                                        if simple:
                                            if s[0] in tabdict:
                                                if s[1] in tabdict[s[0]]:
                                                    st = s[0]
                                                    for v in range(1,len(s)):
                                                        st = st + '.' + s[v]
                                                    tab.append(st)
                                        else:
                                            st = s[0]
                                            for v in range(1,len(s)):
                                                st = st + '.' + s[v]
                                            tab.append(st)
                                        #In either case, we add all formatted tables to tab[]

                                #Now we need to handle making each table into a node, and adding edges between every node
                                #As we are assuming every table is equally interconnected as they are all within the same
                                #select statement and all joined together.

                                #We simply go through tab[] and use dot.node(), then specify the:
                                    #label - What is shown on the graph
                                    #id - What is used to connect the nodes
                                    #color - the color corresponding to the parent object.
                                #The conn condition refers to whether we want the same table, if referenced by multiple objects
                                #to only occupy one node, or whether we want each object's reference to that table to be its own
                                #node. We do this by either making the nodeid (what is used to determine unique nodes) simply the
                                #name of the table, or the combination of table name and parent object name (the same thing displayed
                                #as the label in either case).
                                for t in tab:
                                    if conn:
                                        nodeid = t.lower()
                                        nodelabel = t+'\n'+currobj
                                    else:
                                        nodeid = t.lower()+'\n'+currobj
                                        nodelabel = t+'\n'+currobj
                                        
                                    dot.node(nodeid, nodelabel, color = colors[col])

                                #Now we go through in a double loop, adding edges for each possible. Duplicates are automatically filtered
                                #by the condition "String = True" when we created the dot object. If conn is true we use just the table names,
                                #but if conn is false then we use the combination of table and object names to connect them.

                                #If edges is true we label the edges with the object that created them, otherwise we don't.
                                for t in tab:
                                    for t1 in tab:
                                        if t != t1:
                                            if conn:
                                                node1id = t.lower()
                                                node2id = t1.lower()
                                            else:
                                                node1id = t.lower()+'\n'+currobj
                                                node2id = t1.lower()+'\n'+currobj

                                            if edges:
                                                dot.edge(node1id,node2id,label=currobj, color = colors[col])
                                            else:
                                                dot.edge(node1id,node2id, color = colors[col])

                                

                            break

                #If we find the word "GO" we know we have reached the end of this particular object, and need to continue.
                end = re.match(r'go',lines[line],re.I)
                if end:
                    break

    dot.graph_attr['overlap'] = "scalexy"

    #Neato attempts to spread out the graph as spherical as possible. It is a user option in the GUI.
    if neato:
        dot.graph_attr['layout'] = "neato"
    
    dot.format = 'svg'
    dot.render(view=True)
    #This graph is saved, but it is here automatically rendered to the user in svg format.

def findRef(regex, line, lines, endcon):
    #Generic command used by each of the objects to find the tables that are referenced by the given particular object.
    #regex - The regular expression that will be used to match to possible table formats.
    #line - The current line we are on (usually one line after the CREATE OBJECT line)
    #lines - The list of all lines in the sql file.
    #endcon - Different objects can have different ending conditions, so we account for that by making this customizable.

    #dic will contain all of the different tables we found, properly formatted, and with the value of the type of access made to that table.
    dic = {}
    #Used to record whether we read or write access the table.
    read = False
    write = False

    #Look through each line, using regex to find table references.
    for i in range(line+1,len(lines)):
        find = re.findall(regex, lines[i])

        #Whenever we find a table we need to find whether it is being written to, or read from.
        if find:
            #To do this we iterate over the lines (backwards) to find which of the following words is applied to the table.
            #This method is fairly simple and could likely be improved.
            j = i
            while j > line:

                select = re.search(r'SELECT',lines[j],re.I)
                if select:
                    read = True
                    break

                update = re.search(r'UPDATE',lines[j],re.I)
                if update:
                    write = True
                    break

                into = re.search(r'INTO',lines[j],re.I)
                if into:
                    write = True
                    break

                insert = re.search(r'INSERT',lines[j],re.I)
                if insert:
                    write = True
                    break

                delete = re.search(r'DELETE',lines[j],re.I)
                if delete:
                    write = True
                    break

                _from = re.search(r'FROM',lines[j],re.I)
                if _from:
                    read = True
                    break

                join = re.search(r'JOIN',lines[j],re.I)
                if join:
                    read = True
                    break

                j = j - 1
                
            #Now we need to take the list of tables found on this individual line and simplit them all up into the proper formatting.
            for f in range(len(find)):
                midchar = re.findall(r'\](.)\[',find[f], re.I)
                for c in midchar:
                    if c != '.':
                        continue
                    
                s = re.findall(r'\[(.+?)\]', find[f], re.I)

                if not s:
                    s = re.split(r'\.', find[f], re.I)

                s.append("None")#We append "none" for now, we will replace this later with the proper word.
                
                dic = makeDic(s, dic)#Calls the recursive function. See it for formatting details.

        #If we find the endcon or "GO" we know this object has ended, and we make break.
        if endcon in lines[i]:
            break
        elif lines[i].startswith("GO"):
            break

    if(write and read):
        tag = "Both"
    elif(read):
        tag = "Read"
    elif(write):
        tag = "Write"
    else:
        tag = "None"

    #Rather complicated code to be used to set the tag. This should probably be done recursively, or redone entirely.
    #I think the tag should be set earlier, but there is some reason I did it this way. This function could be slightly retuned.
    if dic != {}:
        for one in dic:
            if type(dic[one]) != str:
                for two in dic[one]:
                    if type(dic[one][two]) != str:
                        for three in dic[one][two]:
                            if type(dic[one][two][three]) != str:
                                for four in dic[one][two][three]:
                                    if type(dic[one][two][three]) != str:
                                        print("Error")
                                    else:
                                        dic[one][two][three][four] = tag
                            else:
                                dic[one][two][three] = tag
                    else:
                        dic[one][two] = tag
            else:
                dic[one] = tag

    #Return the dictionary containing tables we have found.
    return dic

def assocTable(dic):
    #Take the dictinary from the GUI containing all info
    #Split it up into table and other, to find correlation between the two.
    #This will use the referenced found in findRef to mark down connections between tables and
    #the objects that reference them.
    assoc = {}
    
    table = dic["Table"]
    view = dic["View"]
    other = {}
    
    for d in dic:
        if d != "Table" and d != "Assoc":
            other[d] = dic[d]
  
    for key in other:
        #For each of the data types create a dict
        assoc[key] = {}
        for objdb in other[key]:
            #For each object's db of that data type...
            for objname in other[key][objdb]:
                #For each object of that data type
                #Create v, a combo of object database and name
                v = objdb+'.'+objname
                #If this object v is not already in our dict, add it
                if v not in assoc[key]:
                    assoc[key][v] = {}
                #Look into the objects listed under v
                for db in other[key][objdb][objname]:
                    if db in table.keys():
                        for tab in other[key][objdb][objname][db]:
                            if tab in table[db].keys():
                                t = db+'.'+tab
                                #print("Database/Table Match:",v,t)

                                if t not in assoc[key][v]:
                                    #assoc[key][v][t] = {}
                                    assoc[key][v][t] = other[key][objdb][objname][db][tab]

                if len(assoc[key][v].keys()) == 0:
                    #print(key, v)
                    assoc[key].pop(v)
    dual = {}
    assoc1 = {}

    for typ in assoc:
        #Look through each type, view, func, etc.
        for obj in assoc[typ]:
            #Look through each object of that type, dbo.obj, dbo.obj2
            #print(len(assoc[typ][obj].keys()))
            for table in assoc[typ][obj]:
                #Look through each table associated with that object
                #print(typ,obj,table)

                #Assoc1 in format of Table:Type:Object of that Type that references that table
                
                if table not in assoc1.keys():
                    assoc1[table] = {}

                if typ not in assoc1[table].keys():
                    assoc1[table][typ] = {}

                if obj not in assoc1[table][typ].keys():
                    assoc1[table][typ][obj] = {}
                    assoc1[table][typ][obj] = assoc[typ][obj][table]
    
    dual["TopDown"] = assoc
    dual["BottomUp"] = assoc1

    #Return this new dictionary, will be stored in GUI as "Assoc"
    return dual

def removeInvalid(dic, table):
    #Basic idea is to remove any aliases or anything else invalid that slipped through.
    keys1 = list(dic.keys())
    keys2 = list(table.keys())
    valid = keys1 + keys2
    todel = []

    #Go through, checking each of the objects for validity. If they are not valid, add them to todel[]
    #Check for validity against the list of tables previously found.
    for db in dic:
        for obj in dic[db]:
            for ref in dic[db][obj]:
                if ref in valid:

                    for ref2 in dic[db][obj][ref]:
                        if type(dic[db][obj][ref][ref2]) != str:
                            d = [db,obj,ref]
                            if d not in todel:
                                todel.append(d)
                        else:
                            continue
                    
                    continue

                for ref2 in dic[db][obj][ref]:
                    if ref2 in valid:
                        continue
                    else:
                        d = [db,obj,ref]
                        if d not in todel:
                            todel.append(d)
                            
    #Remove all of the invalid entries from dic based on what we have inserted into todel[].
    for d in todel:
        try:
            del dic[d[0]][d[1]][d[2]]
        except:
            print("Exception when deleting invalid objects.")
            continue

    #Return the pruned dictionary.
    return dic    

def findTables(filedir):
    #Parse through the program, look for CREATE TABLE statements.
    #When we find CREAT TABLE, look after for the [Database].[Table]
    #Convert this to {Database:{Table:{}}}
    #Add this to tables{}, until we have a JSON style formatted dict of db/table dicts.
    print("Finding tables in",filedir)

    lines = getLines(filedir)#Get the list of lines from the .sql file.
    
    tables = {}#Create a dict to hold the dicts of tables.

    print("Searching lines for table creations...")
    for i in range(len(lines)):
        match = re.match(r'\s*CREATE\s+TABLE\s+(\[.+\]).(\[.+\])',lines[i],re.I)
        if match:
            db = match.group(1)
            db = db.replace('[','')
            db = db.replace(']','')
            table = match.group(2)
            table = table.replace('[','')
            table = table.replace(']','')
            if db in tables:
                tables[db][table] = {}
            else:
                tables[db] = {}
                tables[db][table] = {}

    return tables

def findViews(filedir):
    #Parse through the program, look for CREATE VIEW statements.
    #When we find CREATE VIEW, look after for the [Database].[View]
    #Convert this to {Database:{View:{}}}
    #Within the deepest part of the dict add the tables this view references, and
    #then within that add the final value as a string of the type of access.
    #Add this to views{}, until we have a JSON style formatted dict of db/view dicts.
    print("Finding views in",filedir)

    lines = getLines(filedir)#Get the list of lines from the .sql file.
            
    views = {}#Create a dict to hold the nested dict of views.

    print("Searching lines for views creations...")
    for i in range(len(lines)):
        #Search until we find a CREATE VIEW statement
        match = re.match(r'\s*CREATE\s+VIEW\s+(\[.+\]).(\[.+\])',lines[i],re.I)
            
        if match:
            #Once we find a view, we need to look forward to find all table references.
            #Look to the findRef function for details. FindRef and the regex used are the
            #most obvious points of improvement for this program.

            #Create a dict for each of these, then use the built in parameter | to combine them
            #Preferring three part to two part, to make sure [One].[Two] is not preferred to [One].[Two].[Three]
            f = {}
            
            f2normal = findRef(r'(?<!\S)\w+\.\w+(?!\S)',i,lines,r"GO")
            f3normal = findRef(r'(?<!\S)\w+\.\w+\.\w+(?!\S)',i,lines,r"GO")
            f2 = findRef(r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',i,lines,r"GO")
            f3 = findRef(r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',i,lines,r"GO")
            f4 = findRef(r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',i,lines,r"GO")

            f = f | f2normal
            f = f | f3normal
            f = f2 | f3
            
            if f4:
                f = f | f4

            #db is the database the view is within
            #v is the name of the view
            #froms is the set of tables referenced by view v
            #therefore views[db][v] will contain the tables referenced by view v
            db = match.group(1)
            db = db.replace('[','')
            db = db.replace(']','')
            v = match.group(2)
            v = v.replace('[','')
            v = v.replace(']','')
            
            if db in views:
                views[db][v] = f
            else:
                views[db] = {}
                views[db][v] = f
    
    return views

def findFunctions(filedir):
    #All these functions work the same way. Check findViews for comments and specifications.
    #In future they should likely be condensed into a singular generic function. When designing
    #I thought it was more likely that there would be severe differences between the syntaxes
    #of the different objects, but they are all practically identical.
    print("Finding functions in",filedir)
    
    lines = getLines(filedir)
            
    functions = {}

    write = False
    read = False
    tag = ""

    print("Searching lines for function creations...")
    for i in range(len(lines)):
        match = re.match(r'\s*CREATE\s+FUNCTION\s+(\[.+\]).(\[.+?\])',lines[i],re.I)
        if match:
            f = {}
            f2 = findRef(r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',i,lines,r"END")
            f3 = findRef(r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',i,lines,r"END")
            f4 = findRef(r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',i,lines,r"END")

            f = f2 | f3

            if f4:
                f = f | f4

            for j in range(i,len(lines)):
                end = re.match(r'END',lines[j])
                if(end):
                    break
                
                insert = re.search(r'INSERT',lines[j],re.I)
                if insert:
                    write = True

                update = re.search(r'UPDATE',lines[j],re.I)
                if update:
                    write = True

                select = re.search(r'SELECT',lines[j],re.I)
                if select:
                    read = True

            if(write and read):
                tag = "Both"
            elif(read):
                tag = "Read"
            elif(write):
                tag = "Write"
            else:
                tag = "None"

            write = False
            read = False
            
            db = match.group(1)
            db = db.replace('[','')
            db = db.replace(']','')
            function = match.group(2)
            function = function.replace('[','')
            function = function.replace(']','')
            
            if db in functions:
                functions[db][function] = f
            else:
                functions[db] = {}
                functions[db][function] = f
    
    return functions

def findProcedures(filedir):
    #All these functions work the same way. Check findViews for comments and specifications.
    #In future they should likely be condensed into a singular generic function. When designing
    #I thought it was more likely that there would be severe differences between the syntaxes
    #of the different objects, but they are all practically identical.
    print("Finding procedures in",filedir)
    
    lines = getLines(filedir)
            
    procedures = {}

    write = False
    read = False
    tag = ""

    print("Searching lines for procedure creations...")
    for i in range(len(lines)):
        match = re.match(r'\s*CREATE\s+PROC\w*\s+(\[.+\]).(\[.+?\])',lines[i],re.I)
        if match:
            f = {}
            f2 = findRef(r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',i,lines,r"END")
            f3 = findRef(r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',i,lines,r"END")
            f4 = findRef(r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',i,lines,r"END")

            f = f2 | f3

            if f4:
                f = f | f4

            for j in range(i,len(lines)):
                end = re.match(r'END',lines[j][0:3])
                if(end):
                    break
                
                insert = re.search(r'INSERT',lines[j],re.I)
                if insert:
                    write = True

                update = re.search(r'UPDATE',lines[j],re.I)
                if update:
                    write = True

                select = re.search(r'SELECT',lines[j],re.I)
                if select:
                    read = True

            if(write and read):
                tag = "Both"
            elif(read):
                tag = "Read"
            elif(write):
                tag = "Write"
            else:
                tag = "None"

            write = False
            read = False
            
            db = match.group(1)
            db = db.replace('[','')
            db = db.replace(']','')
            procedure = match.group(2)
            procedure = procedure.replace('[','')
            procedure = procedure.replace(']','')
            
            if db in procedures:
                procedures[db][procedure] = f
            else:
                procedures[db] = {}
                procedures[db][procedure] = f
    
    return procedures

def findTriggers(filedir):
    #All these functions work the same way. Check findViews for comments and specifications.
    #In future they should likely be condensed into a singular generic function. When designing
    #I thought it was more likely that there would be severe differences between the syntaxes
    #of the different objects, but they are all practically identical.
    print("Finding triggers in",filedir)
    
    lines = getLines(filedir)
            
    triggers = {}

    write = False
    read = False
    tag = ""

    print("Searching lines for trigger creations...")
    for i in range(len(lines)):
        match = re.match(r'\s*CREATE\s+TRIGGER\s+(\[.+\]).(\[.+?\])',lines[i],re.I)
        if match:
            f = {}
            f2 = findRef(r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',i,lines,r"END")
            f3 = findRef(r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',i,lines,r"END")
            f4 = findRef(r'(?<!\S)\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\]\.\[[^\]+]+\](?!\S^;)',i,lines,r"END")

            f = f2 | f3

            if f4:
                f = f | f4

            for j in range(i,len(lines)):

                end = re.match(r'END',lines[j][0:3])
                if(end):
                    break
                
                insert = re.search(r'INSERT',lines[j],re.I)
                if insert:
                    write = True

                update = re.search(r'UPDATE',lines[j],re.I)
                if update:
                    write = True

                select = re.search(r'SELECT',lines[j],re.I)
                if select:
                    read = True

            if(write and read):
                tag = "Both"
            elif(read):
                tag = "Read"
            elif(write):
                tag = "Write"
            else:
                tag = "None"

            write = False
            read = False
            
            db = match.group(1)
            db = db.replace('[','')
            db = db.replace(']','')
            trigger = match.group(2)
            trigger = trigger.replace('[','')
            trigger = trigger.replace(']','')
            
            if db in triggers:
                triggers[db][trigger] = f
            else:
                triggers[db] = {}
                triggers[db][trigger] = f

    return triggers

def disam(command, filedir):
    #Allows for generic command to be passed to find the requested object type within the file.
    if command == "table":
        return findTables(filedir)
    elif command == "view":
        return findViews(filedir)
    elif command == "function":
        return findFunctions(filedir)
    elif command == "procedure":
        return findProcedures(filedir)
    elif command == "trigger":
        return findTriggers(filedir)
    else:
        print("Invalid argument",command,"passed...")
        sys.exit(0)

def main():
    #Standalone main to be used if we want to call this script in isolation.
    args = sys.argv[1:]

    if not args:
        print("Usage: sqlfile [--[table|view|function|procedure|trigger]]")
        sys.exit(0)

    print("Arguments passed:",args)

    if os.path.isfile(args[0]):
        filedir = args[0]
        del args[0]
    else:
        print("Not passed proper file directory/file does not exist")
        sys.exit(0)


    print("SQL File to be parsed located at",filedir)

    sql = {}
    
    for arg in args:
        currdict = disam(arg[2:], filedir)
        print(os.path.splitext(filedir)[0])
        savedir = os.path.basename(filedir)[0:-4]+'.'+arg[2:]+'.json'
        print('\n',arg[2:].capitalize(),'dictionaries:',currdict.keys(),'saved in',savedir,'\n')
        with open(savedir,'w') as convert_file:
            convert_file.write(json.dumps(currdict))

        #with open(savedir) as json_file:
        #    data = json.load(json_file)

        #print(json.dumps(data,indent = 4, sort_keys = True))

if __name__ == '__main__':
    main()
