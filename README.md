# DT-Translators
The the two files of translators are model_translator.py and Cypher2sqlTranslator.py
Please make sure you have installed python in your computer
In addition to python, please install antlr4 by using the below code in terminal
<pre>
pip install antlr4-python3-runtime
</pre>
Then to use model_translator.py, you should make sure you have installed psycopg2 in your computer to connect to Postgres database and the fluent running of code
To install psycopg2 you can use the below code in your terminal
<pre>
  pip install psycopg2
</pre>

The test_of_translator.ipynb can be used in python jupyter notebook to conduct test of two translators, and the example test codes have been covered in it

Furthermore, if you haven't used python and there are some errors related to numpy and pandas below are the codes for installing them
<pre>
pip3 install numpy
pip3 install pandas
</pre>
Moreover, for model_translator, due to some syntax restriction of SQL and Cypher, the name of table are wrapped in "" e.g. "Product", please be aware of it when you try to test in your database after transformation.
And for query translator, please add label at least once for the symbol of node and edge to make sure the correct output of result due to the weakness of SQL.
<pre>
e.g. MATCH (a:Account {isBlocked:'no'}) −[:isLocatedIn]−>(g:City {name:'Ankh−Morpork'}) <−[:isLocatedIn]−(b:Account {isBlocked:'yes'}), p = (a)−[e:Transfer*2]−>(b) WHERE e.amount> 100 RETURN a.owner, b.owner LIMIT 10
</pre>

for you can remove symbol like isLocatedIn edge but you should add label for each symbol at least once such as a,b,e,g
