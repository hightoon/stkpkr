"""
  Stock Analysis
  Trading data format:
  date  opening  highest  close  lowest  volume(shares)  volume(cny)
"""
# -*- coding: utf-8 -*-

import urllib2
import xlrd
import re
import logging
from datetime import datetime
#from pychartdir import *
#from FinanceChart import *
from HTMLParser import HTMLParser


class MyHTMLParser(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)
    self._data = {}
    self._is_date = False
    self._today = None
    self._is_trading_data = False
    self._trade_data = []

  def handle_starttag(self, tag, attrs):
    dict_attrs = dict(attrs)
    if tag == 'a' and ('target', '_blank') in attrs and 'quotes_service' in dict_attrs['href']:
      self._is_date = True
    elif tag == 'div' and self._today is not None:
      self._is_trading_data = True

  def handle_endtag(self, tag):
    if tag == 'a' and self._is_date is True:
      self._is_date = False
    elif tag == 'div' and self._is_trading_data is True:
      self._is_trading_data = False
    elif tag == 'tr' and self._today is not None:
      self._data[tuple(self._today)] = map(float, self._trade_data)
      self._today = None
      self._trade_data = []

  def handle_data(self, data):
    if self._is_date is True:
      self._today = map(int, data.strip().split('-'))
    if self._is_trading_data is True:
      self._trade_data.append(data.strip())

  def get(self):
    return self._data

class GfHTMLParser(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)
    self._data = {}
    self._is_data = False
    self._item = None

  def handle_starttag(self, tag, attrs):
    dict_attrs = dict(attrs)
    if tag == 'table' and dict_attrs.has_key('class') and 'historical_price' in dict_attrs['class']:
      self._is_data = True
    elif self._is_data and tag == 'tr' and dict_attrs.has_key('class') and 'bb' not in dict_attrs['class']:
      self._item = None
    elif tag == 'td' and self._item == None:
      self._item = []

  def handle_data(self, data):
    if self._item is not None and self._is_data:
      data = data.strip()
      if data:
        self._item.append(data.strip())

  def handle_endtag(self, tag):
    if tag == 'table' and self._is_data:
      self._is_data = False

  def get(self):
    return self._item



class Period:
  def __init__(self, year, quarter):
    self._year = year
    self._quarter = quarter

  @property
  def year(self):
    return self._year
  @year.setter
  def year(self, y):
    self._year = y

  @property
  def quarter(self):
    return self._quarter
  @quarter.setter
  def quarter(self, q):
    self._quarter = q

class Stock:
  def __init__(self,  name, id, period):
    self._name = name
    self._id = id
    self._period = period

  def _manipulate_url(self):
    base = "http://money.finance.sina.com.cn/corp/go.php/vMS_MarketHistory/"
    return (base + "stockid/%s.phtml?year=%d&jidu=%d"%(
      self._id, self._period.year, self._period.quarter
      ))

  def fetch(self):
    return urllib2.urlopen(self._manipulate_url()).read()

class GooGleFinance:
  def __init__(self, stock, num_of_days=50):
    self._stock = stock
    self._days = num_of_days

  def _man_url(self):
    base = 'http://www.google.com.hk/finance/historical?q='
    if self._stock.startswith('6'):
      stock = 'SHA%%3A%s'%self._stock
    else:
      stock = 'SHE%%3A%s'%self._stock
    return base + stock + '&start=0&num=%d'%self._days

  def fetch(self):
    return urllib2.urlopen(self._man_url()).read()

#class MyFinanceChart(FinanceChart):
#  def __init__(self, pixel):
#    FinanceChart.__init__(self, pixel)

def pick_stock(stockid):
  high, low, opening, close, vol, date = get_google_fin_data(stockid)
  #print date
  if len(close)<4:
    print 'empty'
    pass
  else:
    thirty_avg_vol = sum(vol[1:11])/10
    if drop_for_days(5, close[:5]):
      #print stockid, "going down for 5 days, @%s"%date[0]
      logging.info("%s going down for 5 days, @%s"%(stockid, date[0]))
    #elif up_for_days(3, close) and up_for_days(3, vol):
    #  print stockid, "going up"
    if vol[0] / thirty_avg_vol > 5:
      if close[0] > close[1] and close[0] == high[0]:
        #print stockid, 'rising with large volume, @%s'%date[0]
        logging.info('%s rising with large volume, @%s'%(stockid, date[0]))
    elif vol[-1] and thirty_avg_vol / vol[-1] > 5:
      if close[0] < close[1]*0.9:
        #print stockid, 'declining with small valume, @%s'%date[0]
        logging.info('%s declining with small valume, @%s'%(stockid, date[0]))
    else:
      #print 'average stock: ', stockid
      pass

def drop_for_days(num_of_days, data):
  """
    the stock price/volume that has been going down for num_of_days days
  """
  for i in range(num_of_days-1):
    if data[-1-i] > data[-2-i]:
      pass
    else:
      return False
  return True

def up_for_days(num_of_days, data):
  for i in range(num_of_days-1):
    if data[-1-i] < data[-2-i]:
      pass
    else:
      return False
  return True

def get_stock_data(stkid):
  periods = [Period(2015, 1), Period(2015, 2), Period(2015, 3)]
  stk = [Stock(stkid, stkid, p) for p in periods]
  parser = MyHTMLParser()
  parser.feed('\n'.join([s.fetch() for s in stk]))
  #print sorted(parser.get().keys())
  stockdata = parser.get()
  date = sorted(stockdata.keys())
  highdata = []
  lowdata = []
  opendata = []
  closedata = []
  volume = []

  if date != [] and date[-1][2] == datetime.today().day:
    for d in date:
      highdata.append(stockdata[d][1])
      lowdata.append(stockdata[d][3])
      opendata.append(stockdata[d][0])
      closedata.append(stockdata[d][2])
      volume.append(stockdata[d][-1])
  return highdata, lowdata, opendata, closedata, volume

def get_google_fin_data(stock):
  date = []
  highdata = []
  lowdata = []
  opendata = []
  closedata = []
  volume = []
  gf = GooGleFinance(stock)
  p = GfHTMLParser()

  while True:
    try:
      p.feed(gf.fetch())
      break
    except:
      pass

  raw_data = p.get()
  if raw_data:
    raw_data = raw_data[6:]
    for i in xrange(0, len(raw_data)/6):
      daily_quote = raw_data[i*6:(i+1)*6]
      #print daily_quote
      date.append(daily_quote[0])
      opendata.append(float(daily_quote[1]))
      highdata.append(float(daily_quote[2]))
      lowdata.append(float(daily_quote[3]))
      closedata.append(float(daily_quote[4]))
      volume.append(int(daily_quote[5].replace(',', '')))
  return highdata, lowdata, opendata, closedata, volume, date



if __name__ != '__main__':
  stockid = '600036'
  periods = [Period(2014, 4), Period(2015, 1), Period(2015, 2)]
  stk = [Stock('RongZhiLian', stockid, p) for p in periods]
  parser = MyHTMLParser()
  parser.feed('\n'.join([s.fetch() for s in stk]))
  #print sorted(parser.get().keys())
  stockdata = parser.get()
  date = sorted(stockdata.keys())
  highdata = []
  lowdata = []
  opendata = []
  closedata = []
  volume = []
  for d in date:
    highdata.append(stockdata[d][1])
    lowdata.append(stockdata[d][3])
    opendata.append(stockdata[d][0])
    closedata.append(stockdata[d][2])
    volume.append(stockdata[d][-1])

  # Create a XYChart object of size 600 x 350 pixels
  c = XYChart(1800, 900)

  # Set the plotarea at (50, 25) and of size 500 x 250 pixels. Enable both the
  # horizontal and vertical grids by setting their colors to grey (0xc0c0c0)
  c.setPlotArea(100, 50, 1500, 600).setGridColor(0xc0c0c0, 0xc0c0c0)

  # Add a title to the chart
  #c.addTitle("Universal Stock Index")

  # Add a custom text at (50, 25) (the upper left corner of the plotarea). Use 12 pts
  # Arial Bold/blue (4040c0) as the font.
  #c.addText(50, 25, "(c) Global XYZ ABC Company", "arialbd.ttf", 12, 0x4040c0)

  # Add a title to the x axis
  #c.xAxis().setTitle("Jan 2001")

  # Set the labels on the x axis. Rotate the labels by 45 degrees.
  xlables = ['%d-%d-%d'%d for d in date]
  c.xAxis().setLabels(xlables).setFontAngle(90)

  # Add a title to the y axis
  #c.yAxis().setTitle("Universal Stock Index")

  # Draw the y axis on the right hand side of the plot area
  c.setYAxisOnRight(1)

  # Add a CandleStick layer to the chart using green (00ff00) for up candles and red
  # (ff0000) for down candles
  layer = c.addCandleStickLayer(highdata, lowdata, opendata, closedata, 0xff0000,
      0x00ff00)

  # Set the line width to 2 pixels
  layer.setLineWidth(3)

  # Output the chart
  c.makeChart("candlestick.png")

  #----------------------------------------------------------------------------#
  # Create a FinanceChart object of width 640 pixels
  c = MyFinanceChart(1240)

  # Add a title to the chart
  c.addTitle(stockid)

  # Set the data into the finance chart object
  timestamp = [chartTime(d[0], d[1], d[2]) for d in date]
  c.setData(timestamp, highdata, lowdata, opendata, closedata, volume, 30)

  # Add the main chart with 240 pixels in height
  c.addMainChart(500)

  # Add a 5 period simple moving average to the main chart, using brown color
  c.addSimpleMovingAvg(5, 0x663300)

  # Add a 20 period simple moving average to the main chart, using purple color
  c.addSimpleMovingAvg(20, 0x9900ff)

  # Add HLOC symbols to the main chart, using green/red for up/down days
  c.addHLOC(0xcc0000, 0x008000)

  # Add 20 days bollinger band to the main chart, using light blue (9999ff) as the
  # border and semi-transparent blue (c06666ff) as the fill color
  c.addBollingerBand(20, 2, 0x9999ff, 0xc06666ff)

  # Add a 75 pixels volume bars sub-chart to the bottom of the main chart, using
  # green/red/grey for up/down/flat days
  c.addVolBars(75, 0xff9999, 0x99ff99, 0x808080)

  # Append a 14-days RSI indicator chart (75 pixels high) after the main chart. The
  # main RSI line is purple (800080). Set threshold region to +/- 20 (that is, RSI = 50
  # +/- 25). The upper/lower threshold regions will be filled with red (ff0000)/blue
  # (0000ff).
  c.addRSI(105, 14, 0x800080, 20, 0xff0000, 0x0000ff)

  # Append a 12-days momentum indicator chart (75 pixels high) using blue (0000ff)
  # color.
  c.addMomentum(105, 12, 0x0000ff)

  c.addMACD(105, 5, 15, 30, 0xff0000, 0x00ff00, 0x0000ff)

  # Output the chart
  c.makeChart(stockid+".png")

else:
  logging.basicConfig(filename='stocks.log', format='%(asctime)s %(message)s', level=logging.DEBUG)
  table = xlrd.open_workbook('astocks.xls').sheets()[0]
  nrows, ncols = table.nrows, table.ncols
  p = re.compile('\d+')
  print 'start searching good stocks...'
  for r in range(nrows):
    id = p.findall(str(table.cell(r, 0)))
    if id != []:
      try:
        pick_stock(id[0].strip(''))
        #get_google_fin_data(id[0].strip(''))
      except KeyboardInterrupt:
        import sys
        sys.exit()
