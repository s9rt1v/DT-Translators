import os, os.path
import math
import pandas as pd
import numpy as np
import psycopg2
import json

#for user to connect to postgres database
def psqlConnect(dbname, user, pwd, host, port):
    global conn
    global cur
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=pwd,
            host=host,
            port=port
        )
        print("Successfully connected to the database.")
        cur = conn.cursor()
    except psycopg2.Error as e:
        print(f"An error occurred while connecting to the database: {e}")
#load Apache AGE extension to enable Cypher in postgresql    
def load_age():
    try:
        cur.execute("LOAD 'age';")
    except psycopg2.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    
    try:
        cur.execute("SET search_path TO ag_catalog;")
    except psycopg2.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
        
#execute the query
def execute(query):
    try:
        cur.execute(query)
        conn.commit()
    except psycopg2.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
        raise

def execute_n_fetch(query):
    try:
        cur.execute(query)
        conn.commit()
        rows = cur.fetchall()
    except psycopg2.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
        raise

#get the label list of all nodes from graph
def get_node_labels(graph_name):
    query = f"SELECT * FROM cypher('{graph_name}', $$MATCH (n) RETURN DISTINCT labels(n)$$) AS (label agtype);"
    labels = []
    try:
        cur.execute(query)
        conn.commit()
        rows = cur.fetchall()
        for row in rows:
            label = row[0].split('"')[1]
            labels.append(label)
    except psycopg2.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
        raise
    return labels
#get the property name list of node with label node_label from graph graph_name
def get_node_property_names(graph_name,node_label):
    query = f"SELECT * FROM cypher('{graph_name}', $$ MATCH (n:{node_label})RETURN DISTINCT keys(n) LIMIT 1 $$) AS (properties agtype);"
    property_names = []
    try:
        cur.execute(query)
        conn.commit()
        rows = cur.fetchall()
        for row in rows:
            p_names = row[0]
            names = json.loads(p_names)
            for name in names:
                property_names.append(name)
    except psycopg2.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
        raise
    return property_names

#get the label list of all edges from graph, the label of each edge consist of {'edge_label': ,'source_label':, 'target_label'}
def get_edge_labels(graph_name):
    query = f"SELECT * FROM cypher('{graph_name}', $$ MATCH (s)-[r]->(t) RETURN DISTINCT labels(s),TYPE(r),labels(t) $$) AS (s_l agtype,r_l agtype, t_l agtype);"
    execute(query)
    rows = cur.fetchall()
    labels = []
    for row in rows:
        infos = {}
        infos['e_label'] = row[1].split('"')[1]
        infos['s_label'] = row[0].split('"')[1]
        infos['t_label'] = row[2].split('"')[1]
        labels.append(infos)
        
    return labels

#get the property name list of edge with label edge_label from graph graph_name, if no property, it will return []
def get_edge_property_names( graph_name,edge_label):
    query = f"SELECT * FROM cypher('{graph_name}', $$ MATCH ()-[r:{edge_label}]->() RETURN DISTINCT keys(r) LIMIT 1 $$) AS (properties agtype);"
    property_names = []
    try:
        cur.execute(query)
        conn.commit()
        rows = cur.fetchall()
        for row in rows:
            p_names = row[0]
            names = json.loads(p_names)
            for name in names:
                property_names.append(name)
    except psycopg2.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
        raise
    return property_names

#get the number of node with label label
def get_num_node_label(graph,label):
    query = f"SELECT * FROM cypher ('{graph}', $$ MATCH (n:{label}) RETURN count(n) $$) as (count agtype);"
    execute(query)
    rows = cur.fetchall()
    return int(rows[0][0])

#get the number of edge with label label
def get_num_edge_label(graph,label):
    query = f"SELECT * FROM cypher ('{graph}', $$ MATCH ()-[r:{label}]->() RETURN count(r) $$) as (count agtype);"
    execute(query)
    rows = cur.fetchall()
    return int(rows[0][0])

#use json to tranform the query result related to node to dictionary
def njson_processor(text):
    t_n = text.split('::vertex')[0]
    t_json = json.loads(t_n)
    return t_json

#create the relation model table for node with label n_label
def node_table_creator(graph,p_names,n_label):
    pre = f"DROP TABLE IF EXISTS \"{n_label}\";"
    execute(pre)
    table_para = 'ID BIGINT PRIMARY KEY'
    if p_names:
        q = ''
        for name in p_names:
            if q == '':
                q = f"SELECT * FROM cypher ('{graph}', $$ MATCH (n:{n_label}) WHERE n.{name} IS NOT NULL "
            else:
                q = q + f"AND n.{name} IS NOT NULL "
        q = q + "RETURN n LIMIT 1 $$) AS (a agtype);"
        execute(q)
        rows = cur.fetchall()
        js = njson_processor(rows[0][0])
        p_values = js['properties']
        for name in p_names:
            value = p_values[name]
            if type(value) == str:
                table_para = table_para + ", " + name + " TEXT"
            elif type(value) == int:
                if value > 2147483647 or value <  -2147483648:
                    table_para = table_para + ", " + name + " BIGINT"
                else:
                    table_para = table_para + ", " + name + " INTEGER"
            elif type(value) == float:
                table_para = table_para + ", " + name + " DECIMAL"
    query = f"CREATE TABLE \"{n_label}\" ({table_para});"
    execute(query)
    
#get all the nodes with label label
def get_nodes(graph, label):
    query = f"SELECT * FROM cypher ('{graph}',$$ MATCH (n:{label}) RETURN n $$) AS (a agtype);"
    execute(query)
    rows = cur.fetchall()
    return rows

#insert the data of nodes with label n_label into table of relation model
def node_data_transformer(graph,p_names,n_label):
    n_num = get_num_node_label(graph,n_label)
    nodes = get_nodes(graph, n_label)
    for i in range(n_num):
        js = njson_processor(nodes[i][0])
        p_values = js['properties']
        ID = js['id']
        cols = 'ID'
        if p_names:
            values = ''
            for name in p_names:
                cols = cols + ', ' + name
                value = p_values[name]
                if type(value) == str:
                    if values == '':
                        values = "'" + str(value) + "'"
                    else:
                        values = values + ", '"  + str(value) + "'"
                else:
                    if values == '':
                        values = str(value)
                    else:
                        values = values + ", "  + str(value)
            query = f"INSERT INTO \"{n_label}\" ({cols}) VALUES ({ID}, {values});"
        else:
            query = f"INSERT INTO \"{n_label}\" ({cols}) VALUES ({ID});"
        
        execute(query)
#use json to tranform the query result related to edges to dictionary
def ejson_processor(text):
    t_n = text.split('::edge')[0]
    t_json = json.loads(t_n)
    return t_json

#create the relation table for edges with label n_label
def edge_table_creator(graph,p_names,e_label):
    label = e_label['e_label']
    s_label = e_label['s_label']
    t_label = e_label['t_label']
    pre = f"DROP TABLE IF EXISTS \"{label}\";"
    execute(pre)
    table_para = f"ID BIGINT PRIMARY KEY, \"{s_label}(s)\" BIGINT, \"{t_label}(t)\" BIGINT"
    if p_names:
        q = ''
        for name in p_names:
            if q == '':
                q = f"SELECT * FROM cypher ('{graph}', $$ MATCH ()-[r:{label}]->() WHERE r.{name} IS NOT NULL "
            else:
                q = q + f"AND r.{name} IS NOT NULL "
        q = q + "RETURN r LIMIT 1 $$) AS (a agtype);"
        execute(q)
        rows = cur.fetchall()
        js = ejson_processor(rows[0][0])
        p_values = js['properties']
        for name in p_names:
            value = p_values[name]
            if type(value) == str:
                table_para = table_para + ", " + name + " TEXT"
            elif type(value) == int:
                if value > 2147483647 or value <  -2147483648:
                    table_para = table_para + ", " + name + " BIGINT"
                else:
                    table_para = table_para + ", " + name + " INTEGER"
            elif type(value) == float:
                table_para = table_para + ", " + name + " DECIMAL"
    table_para = table_para + ", " + f"FOREIGN KEY (\"{s_label}(s)\") REFERENCES \"{s_label}\" (ID), FOREIGN KEY (\"{t_label}(t)\") REFERENCES \"{t_label}\" (ID)"
    query = f"CREATE TABLE \"{label}\" ({table_para});"
    execute(query)

#get all the edges with label label
def get_edges(graph, label):
    query = f"SELECT * FROM cypher('{graph}', $$MATCH ()-[r:{label}]->() RETURN r $$) as ( r agtype);"
    execute(query)
    rows = cur.fetchall()
    return rows

#insert the data of edges with label n_label into table of relation model
def edge_data_transformer(graph,p_names,e_label):
    e_num = get_num_edge_label(graph,e_label['e_label'])
    edges = get_edges(graph, e_label['e_label'])
    for i in range(e_num):
        js = ejson_processor(edges[i][0])
        p_values = js['properties']
        ID = js['id']
        s_id = js['start_id']
        t_id = js['end_id']
        cols = f"ID, \"{e_label['s_label']}(s)\", \"{e_label['t_label']}(t)\""
        if p_names:
            values = ''
            for name in p_names:
                cols = cols + ', ' + name
                value = p_values[name]
                if type(value) == str:
                    if values == '':
                        values = "'" + str(value) + "'"
                    else:
                        values = values + ", '"  + str(value) + "'"
                else:
                    if values == '':
                        values = str(value)
                    else:
                        values = values + ", "  + str(value)
                
            query = f"INSERT INTO \"{e_label['e_label']}\" ({cols}) VALUES ({ID},{s_id},{t_id},{values});"
        else:
            query = f"INSERT INTO \"{e_label['e_label']}\" ({cols}) VALUES ({ID},{s_id},{t_id});"
        execute(query)
        
def translator(graph):
    n_labels = get_node_labels(graph)
    e_labels = get_edge_labels(graph)
    
    if n_labels:
        for n_label in n_labels:
            properties = get_node_property_names(graph, n_label)
            node_table_creator(graph,properties,n_label)
            node_data_transformer(graph,properties,n_label)
            
    if e_labels:
        for e_label in e_labels:
            properties = get_edge_property_names(graph,e_label['e_label'])
            edge_table_creator(graph,properties,e_label)
            edge_data_transformer(graph,properties,e_label)
    print("Translation Complete!!!")
    conn.close()
