import PySimpleGUI as sg
import Parser as p
import DirGraph as g
import os
import json
from os import listdir
from os.path import isfile, join

"""

Main script that calls functions from the other two scripts (Parser.py and DirGraph.py)
Basic goal is to create a simple GUI for the user to interact with to choose the file they want to parse.
The user then should be able to customize what is parsed, and in what ways that data is displayed.
Currently it can extract what tables, triggers, views, functions and procedures are in a given SQL database.
It will also find interconnections between tables and the other objects.
It can also do a secondary parse to search for joins between tables in all object types, using joins to correlate tables.
It displays what objects there are in simple dictionaries, and relations in graphs.

Dependencies:
pysimplegui
graphviz (needs to be in the NODE)

"""

#Empty Dictionary to hold return values from searching for objects
#Will contain the dicts of tables, triggers, views, functions, procedures, and associations between tables and objects
dic = {}

#This section will find previously parsed databases and import their data
path = os.getcwd()
prev = [f for f in listdir() if isfile(join(path,f))]

rem = []
for f in prev:
    if f[-5:] != '.json':
        rem.append(f)

prev = [x for x in prev if x not in rem]

for i in range(len(prev)):
    prev[i] = prev[i].replace('.json','')
    prev[i] = prev[i].replace('.Function','')
    prev[i] = prev[i].replace('.Procedure','')
    prev[i] = prev[i].replace('.View','')
    prev[i] = prev[i].replace('.Table','')
    prev[i] = prev[i].replace('.Trigger','')
    prev[i] = prev[i].replace('.Assoc','')

prev = list(set(prev))

#This section uses pysimplegui to create a layout, where each sg.Object is an object in the ui, and each line is a line in the GUI
layout = [  [sg.Text('Select your SQL File to be Parsed, or Select Prior SQL File to Import')],
            [sg.InputText(key = "dir"),sg.FileBrowse(),sg.Combo(values=prev,key="prev"),sg.Button('Import')],
            [sg.Text("Select Data to Extract from File:")],
            [sg.Checkbox('Find All',key = "ALL"),sg.Checkbox('Table', key="Tab", default = True), sg.Checkbox('View', key="Vie"), sg.Checkbox('Function', key="Fun"), sg.Checkbox('Procedure', key="Pro"), sg.Checkbox('Trigger', key="Tri")],
            [sg.Button('Parse File'), sg.Button('Associate Tables to Objects')],
            [sg.Text("Select Extracted Data to View:")],
            [sg.Button('Tables'), sg.Button('Views'), sg.Button('Functions'), sg.Button('Procedures'), sg.Button('Triggers'), sg.Button('Associations')],
            [sg.Text("Once you have assocated tables with objects, you can generate a graph:")],
            [sg.Text("(Neato will attempt to spread out the graph, Spline will prevent edges from overlapping nodes)")],
            [sg.Checkbox("Spline", key = "spline"),sg.Checkbox("Neato", key = "neato")],
            [sg.Button("Generate Graph")],
            [sg.Text("Select a SQL file using the browse feature to extract table-table graph.")],
            [sg.Text("Requires BOTH a file in the browse location and data currently imported.")],
            [sg.Text("(Neato will attempt to spread out the graph, Simple will only allow prior extracted tables to be shown)")],
            [sg.Checkbox("Neato", key = "neato2"),sg.Checkbox("Simple", key = "simp"), sg.Checkbox("Connected", key="conn"), sg.Checkbox("Label Edges", key="edges")],
            [sg.Button('Associate Tables to Tables')]]

#Creates the window and names it
window = sg.Window('SQL Parser', layout)
#This loop handles the running of the UI, allowing for more than one action to be taken.
while True:
    #First the values are read from what has been done to the window
    event, values = window.read()
    if event == sg.WIN_CLOSED: #if user closes window or clicks cancel
        break
    #print(event)
    #print(values)

    #If debugging, comment out the try/except, this is here to make it so the program continues running even if an exception occurs...
    #Such as when a non-.sql file is accessed using Browse. Exception is still printed, but to get the full traceback one would either need to
    #use the traceback library, or comment out the try/except branch.
    try:
        if event == "Parse File":
            #If the event is that the Parse File button has been pressed
            #then we need to call the Parser.py function disam, letting it know
            #the type of information we want to extract, and the dic we want to store
            #it back into. We do this for whatever is checked, or everything if "Find All" is checked.
            if values["ALL"]:
                dic['Table'] = p.disam("table",values["dir"])
                dic['View'] = p.disam("view",values["dir"])
                dic['Function'] = p.disam("function",values["dir"])
                dic['Procedure'] = p.disam("procedure",values["dir"])
                dic['Trigger'] = p.disam("trigger",values["dir"])
                dic['View'] = p.removeInvalid(dic['View'],dic['Table'])
                dic['Function'] = p.removeInvalid(dic['Function'],dic['Table'])
                dic['Procedure'] = p.removeInvalid(dic['Procedure'],dic['Table'])
                dic['Trigger'] = p.removeInvalid(dic['Trigger'],dic['Table'])
            else:
                if values["Tab"]:
                    dic['Table'] = p.disam("table",values["dir"])

                if values["Vie"]:
                    dic['View'] = p.disam("view",values["dir"])
                    dic['View'] = p.removeInvalid(dic['View'],dic['Table'])

                if values["Fun"]:
                    dic['Function'] = p.disam("function",values["dir"])
                    dic['Function'] = p.removeInvalid(dic['Function'],dic['Table'])

                if values["Pro"]:
                    dic['Procedure'] = p.disam("procedure",values["dir"])
                    dic['Procedure'] = p.removeInvalid(dic['Procedure'],dic['Table'])

                if values["Tri"]:
                    dic['Trigger'] = p.disam("trigger",values["dir"])
                    dic['Trigger'] = p.removeInvalid(dic['Trigger'],dic['Table'])
            
            
            #Once we have extracted all the information, we save everything to its own
            #.json file, in a format that our re-import code expects.
            for key in dic.keys():
                savedir = os.path.basename(values["dir"])[0:-4] + '.' + key + '.json'
                with open(savedir,'w') as convert_file:
                    convert_file.write(json.dumps(dic[key]))
                    
        elif event == "Import":
            #If the event is to import prior data, we load the saved json files into dic.
            if isfile(values["prev"]+".Table.json"):
                with open(values["prev"]+".Table.json") as json_file:
                    dic["Table"] = json.load(json_file)

            if isfile(values["prev"]+".View.json"):
                with open(values["prev"]+".View.json") as json_file:
                    dic["View"] = json.load(json_file)

            if isfile(values["prev"]+".Trigger.json"):
                with open(values["prev"]+".Trigger.json") as json_file:
                    dic["Trigger"] = json.load(json_file)

            if isfile(values["prev"]+".Procedure.json"):
                with open(values["prev"]+".Procedure.json") as json_file:
                    dic["Procedure"] = json.load(json_file)

            if isfile(values["prev"]+".Function.json"):
                with open(values["prev"]+".Function.json") as json_file:
                    dic["Function"] = json.load(json_file)

            if isfile(values["prev"]+".Assoc.json"):
                with open(values["prev"]+".Assoc.json") as json_file:
                    dic["Assoc"] = json.load(json_file)

        elif event == "Associate Tables to Objects":
            #This code will pass the full dic to the assoctable function,
            #wherin it will associate tables with the objects that reference them.
            #This is then stored into its own dic entry as "Assoc".

            #When parsing normally the creation statement for objects is already scanned for table names,
            #so this is as simple as reading through the dicts we have already made and correlating them to tables
            #in the table dict.
            if "Table" not in dic:
                print("No table")
                continue
            
            assoc = p.assocTable(dic)

            dic["Assoc"] = assoc
            
            fname = ""

            if values["prev"]:
                fname = values["prev"]
            elif values["dir"]:
                fname = os.path.basename(values["dir"])[0:-4]

            with open(fname+".Assoc.json",'w') as convert_file:
                convert_file.write(json.dumps(assoc))

        elif event == "Associate Tables to Tables":
            #This code will do a secondary parse of the database file.
            #It will look for objects, look for select statements, and then look for join statements.
            #Join statements can be used to correlate tables, and we use this to generate a graph of table relations.
            #It uses the prior parsed data to improve its functionality. The graph it creates is saved automatically.
            #Future work could be done in using graphical analysis on the graph generated.
            if not values["dir"]:
                print("No dir value")
                break
            
            fname = os.path.basename(values["dir"])[0:-4]

            other = {}
            
            if dic['Table']:
                other = other | dic['Table']
                
            if dic['View']:
                other = other | dic['View']
                
            if dic['Function']:
                other = other | dic['Function']

            if dic['Procedure']:
                other = other | dic['Procedure']

            if dic['Trigger']:
                other = other | dic['Trigger']
            
            p.findJoins(values["dir"],fname, other, dic["Table"], values["simp"], values["neato2"], values["conn"], values["edges"])
                
        elif event == "Generate Graph":
            #Uses table-object associations to generate a graph, calling the DirGraph.py PrintGraph script to do so.
            if "Assoc" not in dic:
                print("No Assoc")
                continue

            if values["prev"]:
                fname = values["prev"]
            elif values["dir"]:
                fname = os.path.basename(values["dir"])[0:-4]
                
            graph, tables, objs = g.GetGraph(fname+".Assoc.json")

            g.PrintGraph(graph, tables, objs, values["spline"],values["neato"], fname)    
    except Exception as e:
        print("Exception:",e)
        continue

    #This entire section is for displaying to the user the prior extracted data in a json style format.
    if event == "Tables" and "Table" in dic:
        sg.popup_scrolled(json.dumps(dic['Table'], indent = 4, sort_keys = True),title = "Tables")
    elif event == "Views" and "View" in dic:
        sg.popup_scrolled(json.dumps(dic['View'], indent = 4, sort_keys = True),title = "Views")
    elif event == "Functions" and "Function" in dic:
        sg.popup_scrolled(json.dumps(dic['Function'], indent = 4, sort_keys = True),title = "Functions")
    elif event == "Procedures" and "Procedure" in dic:
        sg.popup_scrolled(json.dumps(dic['Procedure'], indent = 4, sort_keys = True),title = "Procedures")
    elif event == "Triggers" and "Trigger" in dic:
        sg.popup_scrolled(json.dumps(dic['Trigger'], indent = 4, sort_keys = True),title = "Triggers")
    elif event == "Associations" and "Assoc" in dic:
        sg.popup_scrolled(json.dumps(dic['Assoc'], indent = 4, sort_keys = True),title = "Associations")
        
    

window.close()
