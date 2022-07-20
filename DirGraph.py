import json
import os
from graphviz import Digraph
import graphviz

def GetGraph(dirassoc):
    #Uses the assoc file to create a directed graph representing those associations.
    #Will return a list of tables and objects, and a 2D array representing the relations between the two.
    with open(dirassoc) as json_file:
        assoc = json.load(json_file)

    dic = assoc["TopDown"]
    tuples = []

    for typ in dic:
        for obj in dic[typ]:
            for table in dic[typ][obj]:
                tuples.append((typ,obj,"Table",table,dic[typ][obj][table])) #Type, Object, Table, Direction

    tables = []
    objs = []

    for i in range(len(tuples)):
        t = (tuples[i][2],tuples[i][3])
        o = (tuples[i][0],tuples[i][1])

        if t not in tables:
            tables.append(t)
            
        if o not in objs:
            objs.append(o)
        

    print(len(tables),len(objs))

    graph = [[0 for i in range(len(objs))] for j in range(len(tables))]

    #1 for write, 2 for read, 3 for both, 4 for none
    for t in range(len(tables)):
        for o in range(len(objs)):
            if (objs[o][0],objs[o][1],tables[t][0],tables[t][1],"Write") in tuples:
                graph[t][o] = 1
            elif (objs[o][0],objs[o][1],tables[t][0],tables[t][1],"Read") in tuples:
                graph[t][o] = 2
            elif (objs[o][0],objs[o][1],tables[t][0],tables[t][1],"Both") in tuples:
                graph[t][o] = 3
            elif (objs[o][0],objs[o][1],tables[t][0],tables[t][1],"None") in tuples:
                graph[t][o] = 4
    
    return graph, tables, objs

    
def PrintGraph(graph, tables, objs, spline, neato, name):
    #Take the graph object (a 2D array representing connections) and convert it to a dot style Directed graph.
    dot = Digraph(name+".D")

    for t in range(len(tables)):
        dot.node(tables[t][1], tables[t][1]+'\n'+tables[t][0])

    for t in range(len(objs)):
        dot.node(objs[t][1], objs[t][1]+'\n'+objs[t][0])

    for i in range(len(graph)):
        for j in range(len(graph[i])):
            if graph[i][j]:
                #print("Connection between", objs[j], tables[i], "with type", graph[i][j])
                v = graph[i][j]

                if v == 1:
                    dot.edge(objs[j][1],tables[i][1])
                elif v == 2:
                    dot.edge(tables[i][1],objs[j][1])
                elif v == 3:
                    dot.edge(tables[i][1],objs[j][1])
                    dot.edge(objs[j][1],tables[i][1])
                elif v == 4:
                    continue

    dot.graph_attr['overlap'] = "scalexy"
    dot.graph_attr['fontsize'] = "10.0"
    dot.graph_attr['concentrate'] = "true"
    dot.graph_attr['sep'] = "+1"

    if spline:
        dot.graph_attr['splines'] = "spline"

    if neato:
        dot.graph_attr['layout'] = "neato"

    
    dot.format = 'svg'
    dot.render(view=True)






















    
