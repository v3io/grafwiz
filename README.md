# grafwiz
Grafana dashboard wizard/generator 

## Usage example

```python

dash = Dashboard("cool", start='now-1d', dataSource='Iguazio')
dash.template(name="SYMBOL", label="Symbol", query="fields=symbol;table_name=stocks;backend=kv;container=bigdata")

tbl = Table('tbl1',span=8).source(table='stocks',fields=['symbol','name','currency','price','last_trade','timezone','exchange'])
log = Ajax(title='Log',url='https://stream-view.iguazio.app.vjszzjiaingr.iguazio-cd0.com/')
dash.row([tbl,log])

dash.row([Graph(metric).series(table="stock_metrics", fields=[metric]) for metric in ['price','volume']])

print(dash.show())

dash.deploy('http://grafana')
```
