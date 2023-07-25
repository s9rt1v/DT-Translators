import numpy as np
import glob
import os, os.path
from antlr4 import *
from CypherLexer import CypherLexer
from CypherParser import CypherParser
from CypherParser import CypherParser
from CypherVisitor import CypherVisitor

class CypherToSqlVisitor(CypherVisitor):
    def __init__(self):
        self.match_count = 0
        self.pattern_count = 0
        self.element_chain_count = 0
        self.sql = 'WITH RECURSIVE recursive_query AS '
        self.non_recursion = ''
        self.recursion = ''
        self.rt = ' '
        self.where_clause = ' '
        self.recursive_where = ''
        self.select = ''
        self.recursive_select = 'SELECT'
        self.from_clause = 'FROM '
        self.tables = []
        self.nodes = []
        self.edges = []
        self.maprole = ''
        self.isRecursive = False
        self.recursiveEdge = []
        self.rangeList = []
        self.path_name = 'temp_query'

    #def visitOC_ReadingClause(self, ctx:CypherParser.OC_ReadingClauseContext):
        
    def visitOC_Match(self, ctx: CypherParser.OC_MatchContext):
        self.match_count += 1
        
        return self.visitChildren(ctx)
    
        
    def visitOC_PatternPart(self, ctx:CypherParser.OC_PatternPartContext):
        if self.element_chain_count>0:
            self.element_chain_count += 1
        #if self.pattern_count > 1:
            #self.pattern[self.pattern_count] += 'UNION ALL '
        if ctx.oC_Variable():
            self.path_name = ctx.oC_Variable().getText()
        
        return self.visitChildren(ctx)
    
    def visitOC_PatternElementChain(self, ctx:CypherParser.OC_PatternElementChainContext):
        self.element_chain_count += 1
        return self.visitChildren(ctx)
    
    def visitOC_NodePattern(self, ctx:CypherParser.OC_NodePatternContext):
        node_dict = {}
        if ctx.oC_Variable():
            node_dict['name'] = ctx.oC_Variable().getText()
            if ctx.oC_NodeLabels():
                if len(ctx.oC_NodeLabels().oC_NodeLabel()) == 1:
                    node_dict['label'] = ctx.oC_NodeLabels().oC_NodeLabel()[0].oC_LabelName().getText()
                    table_name = f"{node_dict['label']} {node_dict['name']}"
                    if table_name not in self.tables:
                        self.tables.append(table_name)
                else:
                    for name in ctx.oC_NodeLabels().oC_NodeLabel():
                        labelname = name.getText()
                        table_name = labelname.lower() + str(self.element_chain_count)
                        node_dict['label'] = {'table_label':labelname, 'table_name':table_name}
                        table_name = f"{node_dict['label']['table_label']} {node_dict['label']['table_name']}"
                        if table_name not in self.tables:
                            self.tables.append(table_name)
        else:
            if ctx.oC_NodeLabels():
                if len(ctx.oC_NodeLabels().oC_NodeLabel()) == 1:
                    labelname = ctx.oC_NodeLabels().oC_NodeLabel()[0].oC_LabelName().getText()
                    node_dict['name'] = labelname.lower() + str(self.element_chain_count)
                    node_dict['label'] = labelname
                    table_name = f"{node_dict['label']} {node_dict['name']}"
                    if table_name not in self.tables:
                        self.tables.append(table_name)
                else:
                    node_dict['name'] = []
                    node_dict['label'] = []
                    for name in ctx.oC_NodeLabels().oC_NodeLabel():
                        labelname = name.getText()
                        node_dict['name'].append(labelname.lower() + str(self.element_chain_count))
                        node_dict['label'].append(labelname)
                        table_name = f"{node_dict['label'][-1]} {node_dict['name'][-1]}"
                        if table_name not in self.tables:
                            self.tables.append(table_name)
        self.nodes.append(node_dict)
        if ctx.oC_Properties():
            self.maprole = 'node'
            self.visit(ctx.oC_Properties().oC_MapLiteral())
            
        #return self.visitChildren(ctx)
    
    def visitOC_MapLiteral(self, ctx:CypherParser.OC_MapLiteralContext):
        keys = ctx.oC_PropertyKeyName()
        values = ctx.oC_Expression()
        properties = []
        for key, value in zip(keys, values):
            properties.append({'key':key.getText(),'value':value.getText()})
            if self.maprole == 'node':
                s = f"{self.nodes[-1]['name']}.{key.getText()} = {value.getText()}"
                self.nodes[-1]['properties'] = properties
            elif self.maprole == 'edge':
                s = f"{self.edges[-1]['name']}.{key.getText()} = {value.getText()}"
                self.edges[-1]['properties'] = properties
            if self.where_clause == ' ':
                self.where_clause += f'WHERE {s}' 
            else:
                self.where_clause = self.where_clause + ' AND ' + s
        
    
    def visitOC_RelationshipPattern(self, ctx:CypherParser.OC_RelationshipPatternContext):
        relation_dict = {}
        if ctx.oC_RelationshipDetail().oC_Variable():
            relation_dict['name'] = ctx.oC_RelationshipDetail().oC_Variable().getText()
            if ctx.oC_RelationshipDetail().oC_RelationshipTypes():
                if len(ctx.oC_RelationshipDetail().oC_RelationshipTypes().oC_RelTypeName()) == 1:
                    labelname = ctx.oC_RelationshipDetail().oC_RelationshipTypes().oC_RelTypeName()[0].getText()
                    relation_dict['label'] = labelname
                    table_name = f"{relation_dict['label']} {relation_dict['name']}"
                    if table_name not in self.tables:
                        self.tables.append(table_name)
                else: 
                    for name in ctx.oC_RelationshipDetail().oC_RelationshipTypes().oC_RelTypeName():
                        labelname = name.getText()
                        table_name = labelname.lower() + str(self.element_chain_count)
                        relation_dict['label'] = {'table_label':labelname, 'table_name':table_name}
                        table_name = f"{relation_dict['label']['table_label']} {relation_dict['label']['table_name']}"
                        if table_name not in self.tables:
                            self.tables.append(table_name)
        else:
            if ctx.oC_RelationshipDetail().oC_RelationshipTypes():
                if len(ctx.oC_RelationshipDetail().oC_RelationshipTypes().oC_RelTypeName()) == 1:
                    labelname = ctx.oC_RelationshipDetail().oC_RelationshipTypes().oC_RelTypeName()[0].getText()
                    relation_dict['name'] = labelname.lower() + str(self.element_chain_count)
                    relation_dict['label'] = labelname
                    table_name = f"{relation_dict['label']} {relation_dict['name']}"
                    if table_name not in self.tables:
                        self.tables.append(table_name)
                else:
                    relation_dict['name'] = []
                    relation_dict['label'] = []
                    for name in ctx.oC_RelationshipDetail().oC_RelationshipTypes().oC_RelTypeName():
                        labelname = name.getText()
                        relation_dict['name'].append(labelname.lower() + str(self.element_chain_count))
                        relation_dict['label'].append(labelname)
                        table_name = f"{relation_dict['label'][-1]} {relation_dict['name'][-1]}"
                        if table_name not in self.tables:
                            self.tables.append(table_name)

        if ctx.oC_LeftArrowHead():
            relation_dict['direction'] = '<'
        elif ctx.oC_RightArrowHead():
            relation_dict['direction'] = '>'
        relation_dict['index'] = self.element_chain_count
        self.edges.append(relation_dict)
        if ctx.oC_RelationshipDetail().oC_Properties():
            self.maprole = 'edge'
            self.visit(ctx.oC_RelationshipDetail().oC_Properties().oC_MapLiteral())
        if ctx.oC_RelationshipDetail().oC_RangeLiteral():
            self.visit(ctx.oC_RelationshipDetail().oC_RangeLiteral())
    
    def visitOC_RangeLiteral(self, ctx:CypherParser.OC_RangeLiteralContext):
        self.isRecursive = True
        self.edges[-1]['range'] = ctx.getText().split('*')[1]
        return self.visitChildren(ctx)
    
    def visitOC_NodeLabel(self, ctx:CypherParser.OC_NodePatternContext):
        
        return self.visitChildren(ctx)
    
    def visitOC_Where(self, ctx:CypherParser.OC_WhereContext):
        s = ctx.oC_Expression().getText()
        if self.where_clause == ' ':
            self.where_clause += f'WHERE {s}' 
        else:
            self.where_clause = self.where_clause + ' AND ' + s
        
        return self.visitChildren(ctx)
    
    # Visit a parse tree produced by CypherParser#oC_Return.
    def visitOC_Return(self, ctx: CypherParser.OC_ReturnContext):
        items = ctx.oC_ProjectionBody().oC_ProjectionItems().getText()
        if 'DISTINCT' in ctx.oC_ProjectionBody().getText():
            self.select = f'SELECT DISTINCT {items} '
        else:
            self.select = f'SELECT {items} '
        return self.visitChildren(ctx)

    def visitOC_Limit(self, ctx:CypherParser.OC_LimitContext):
        limit = ctx.getText()
        self.rt = self.rt + limit + " "
        return self.visitChildren(ctx)
    
    def visitOC_Skip(self, ctx:CypherParser.OC_SkipContext):
        skip = ctx.getText()
        self.rt = self.rt + skip + " "
    
    def visitOC_Order(self, ctx:CypherParser.OC_OrderContext):
        self.rt = self.rt + ctx.getText() + " "
        return self.visitChildren(ctx)
    
    def nodeJudger(self,edge,node, pos):
        node_label = ''
        node_name = ''
        if node:
            node_keys = list(node.keys())
            if 'label' in node_keys:
                node_name = node['name']
                node_label = node['label']
                if 'range' not in list(edge.keys()):
                    s = f"{edge['name']}.\"{node['label']}({pos})\" = {node['name']}.ID"
                    if self.where_clause == ' ':
                        self.where_clause += f'WHERE {s}' 
                    else:
                        self.where_clause = self.where_clause + ' AND ' + s
            else:
                for node_temp in self.nodes:
                    if node_temp['name'] == node['name']:
                        if 'label' in list(node_temp.keys()):
                            node_label = node_temp['label']
                            node_name = node['name']
                            if 'range' not in list(edge.keys()):
                                s = f"{edge['name']}.\"{node_temp['label']}({pos})\" = {node['name']}.ID"
                                if self.where_clause == ' ':
                                    self.where_clause += f'WHERE {s}' 
                                else:
                                    self.where_clause = self.where_clause + ' AND ' + s
        return {'name':node_name,'label': node_label}
    
    def conditionAdder(self):
        for i in range(len(self.edges)):
            edge = self.edges[i]
            if edge:
                edge_keys = list(edge.keys())
                if 'label' in edge_keys:
                    index = edge['index']
                    direction = edge['direction']
                    if direction == '>':
                        node_s = self.nodes[index-1]
                        node_t = self.nodes[index]
                    else:
                        node_t = self.nodes[index-1]
                        node_s = self.nodes[index]
                    from_node = self.nodeJudger(edge,node_s,'s')
                    to_node = self.nodeJudger(edge,node_t,'t')
                    self.edges[i]['start'] = from_node
                    self.edges[i]['end'] = to_node
                    
    def fromAdder(self):
        for table in self.tables:
            temp = table.split(" ")
            temp[0] = f"\"{temp[0]}\""
            if self.from_clause == 'FROM ':
                self.from_clause += f"{temp[0]} {temp[1]}"
            else:
                self.from_clause = self.from_clause + ", " + f"{temp[0]} {temp[1]}"
        tables = self.from_clause.split(",")
                
    def notRecursive(self):
        self.fromAdder()
        self.conditionAdder()
        self.non_recursion = f"{self.select} {self.from_clause} {self.where_clause}"
        self.sql = f'{self.non_recursion}'+ self.rt
        
    def selectAdder(self):
        for edge in self.edges:
            if edge:
                if 'range' in list(edge.keys()):
                    self.recursiveEdge.append(edge)
                    if '..' in edge['range']:
                        temp = edge['range'].split('..')
                        if not temp[0]:
                            temp[0] = str(0)
                        self.rangeList = temp
                    else:
                        self.rangeList = edge['range']
                    edge_name = edge['name']
                    node_s = edge['start']
                    node_t = edge['end']
                    self.recursive_select = f"{self.recursive_select} {edge_name}.\"{node_s['label']}(s)\" AS start, {edge_name}.\"{node_t['label']}(t)\" AS \"end\", ARRAY[{edge_name}.\"{node_s['label']}(s)\",{edge_name}.\"{node_t['label']}(t)\"] AS path, 1 AS depth"
                    if 'properties' in list(edge.keys()):
                        for p in edge['properties']:
                            if self.recursive_where == '':
                                self.recursive_where = f"WHERE {edge_name}.{p['key']} = {p['value']}"
                            else:
                                self.recursive_where = f"{self.recursive_where} AND {edge_name}.{p['key']} = {p['value']}"
                    self.recursion = f"SELECT temp_query.\"end\",{edge_name}.\"{node_s['label']}(t)\",  temp_query.path || {edge_name}.\"{node_s['label']}(t)\", temp_query.depth + 1 FROM \"{edge['label']}\" {edge_name}, recursive_query temp_query WHERE temp_query.\"end\" = {edge_name}.\"{node_s['label']}(s)\""
                    if len(self.rangeList)>1:
                        if self.rangeList[1]:
                            self.recursion = f"{self.recursion} AND temp_query.depth <= {self.rangeList[1]}"
                    elif self.rangeList:
                        self.recursion = f"{self.recursion} AND temp_query.depth <= {self.rangeList[0]}"
                        
    def recursiveFromAdjustor(self):
        tables = self.from_clause.split(",")
        self.from_clause = ''
        for table in tables:
            for edge in self.recursiveEdge:
                if f"\"{edge['label']}\" {edge['name']}" in table:
                    tables.remove(table)
        for table in tables:
            if 'FROM' in table:
                self.from_clause = f"{table}"
            else:
                self.from_clause = f"{self.from_clause}, {table}"
        if 'FROM' not in self.from_clause:
            self.from_clause = f"FROM {self.from_clause}"
            
    def recursiveWhereAdjustor(self):
        conditions =  self.where_clause.split("AND")
        self.where_clause = ''
        for condition in conditions:
            for edge in self.recursiveEdge:
                len_name = len(edge['name'])
                if f" {edge['name']}." == condition[:len_name+2]:
                    if self.recursive_where == '':
                        self.recursive_where = f"WHERE{condition}"
                    else:
                        self.recursive_where = f"{self.recursive_where} AND{condition}"
                    conditions.remove(condition)
        for condition in conditions:
            if 'WHERE' in condition:
                self.where_clause = condition
            else:
                self.where_clause = f"{self.where_clause}AND{condition}"
        if 'WHERE' not in self.where_clause:
            self.where_clause = 'WHERE' + self.where_clause
        node_s_name = self.recursiveEdge[0]['start']['name']
        node_t_name = self.recursiveEdge[0]['end']['name']
        s = f"{node_s_name}.ID = {self.path_name}.path[1] AND {node_t_name}.ID = {self.path_name}.path[{self.path_name}.depth+1]"
        depth_judger = ''
        if len(self.rangeList)>1:
            if self.rangeList[0]:
                depth_judger = f" AND {self.path_name}.depth >= {self.rangeList[0]}"
            if self.rangeList[1]:
                depth_judger = f"{depth_judger} AND {self.path_name}.depth <= {self.rangeList[1]}"
        elif self.rangeList:
            depth_judger = f" AND {self.path_name}.depth = {self.rangeList[0]}"
        s += depth_judger
        if self.where_clause == '':
            self.where_clause = f"WHERE {s}"
        else:
            self.where_clause = f"{self.where_clause} AND {s}"
            
    def recursiveConstructor(self):
        self.conditionAdder()
        self.fromAdder()
        self.selectAdder()
        self.recursiveFromAdjustor()
        self.recursiveWhereAdjustor()
        self.non_recursion = f"{self.recursive_select} FROM \"{self.recursiveEdge[0]['label']}\" {self.recursiveEdge[0]['name']} {self.recursive_where}"
        self.rt = f"{self.select}{self.from_clause}, recursive_query {self.path_name} {self.where_clause}{self.rt}"
        self.sql = f"{self.sql}({self.non_recursion} UNION ALL {self.recursion}) {self.rt}"
        
    def getSql(self):
        if not self.isRecursive:
            self.notRecursive()
        else:
            self.recursiveConstructor()
        return print(self.sql.strip())

def query_translator(query):
    if 'UNION ALL' in query:
        new_query = query.split('UNION ALL')
        for i in range(len(new_query)):
            if i > 0:
                print('UNION ALL')
            input_stream = InputStream(new_query[i])
            lexer = CypherLexer(input_stream)
            token_stream = CommonTokenStream(lexer)
            parser = CypherParser(token_stream)
            tree = parser.oC_Cypher() 
            visitor = CypherToSqlVisitor()
            visitor.visit(tree)
            visitor.getSql()
    elif 'UNION' in query:
        new_query = query.split('UNION')
        for i in range(len(new_query)):
            if i > 0:
                print('UNION')
            input_stream = InputStream(new_query[i])
            lexer = CypherLexer(input_stream)
            token_stream = CommonTokenStream(lexer)
            parser = CypherParser(token_stream)
            tree = parser.oC_Cypher() 
            visitor = CypherToSqlVisitor()
            visitor.visit(tree)
            visitor.getSql()
    else:
        input_stream = InputStream(query)
        lexer = CypherLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = CypherParser(token_stream)
        tree = parser.oC_Cypher() 
        visitor = CypherToSqlVisitor()
        visitor.visit(tree)
        visitor.getSql()
