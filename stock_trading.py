#/usr/bin/python
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
from datetime import datetime, timedelta
from HTMLParser import HTMLParser
from yahoo_finance import Share


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

  def get_historical(self, num_of_days):
    if self._id.startswith('6'):
      stk_id = self._id + '.ss'
    else:
      stk_id = self._id + '.sz'
    stk = Share(stk_id)
    start = datetime.strftime(datetime.today() - timedelta(days=num_of_days+1),
                              '%Y-%m-%d')
    end   = datetime.strftime(datetime.today() - timedelta(days=1),
                              '%Y-%m-%d')
    hist = stk.get_historical(start, end)
    high    = []
    low     = []
    opening = []
    close   = []
    vol     = []
    date    = []
    for d in hist:
      if d.has_key('High'):
        high.append(float(d['High']))
        low.append(float(d['Low']))
        opening.append(float(d['Open']))
        close.append(float(d['Close']))
        vol.append(float(d['Volume']))
        date.append(d['Date'])
    return high, low, opening, close, vol, date

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
  stk = Stock('', stockid, None)
  high, low, opening, close, vol, date = stk.get_historical(45)
  print stockid
  if len(close)<4:
    print 'empty'
  else:
    thirty_avg_vol = sum(vol[1:6])/5
    if drop_for_days(6, close[:6]):
      #print stockid, "going down for 5 days, @%s"%date[0]
      logging.info("%s going down for 5 days, @%s"%(stockid, date[0]))
    #elif up_for_days(3, close) and up_for_days(3, vol):
    #  print stockid, "going up"
    if thirty_avg_vol and vol[0] / thirty_avg_vol > 3:
      if close[0] > close[1] and close[0] == high[0]:
        #print stockid, 'rising with large volume, @%s'%date[0]
        logging.info('%s rising with large volume, @%s'%(stockid, date[0]))
    elif vol[-1] and thirty_avg_vol / vol[-1] > 4:
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


if __name__ == '__main__':
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
      except KeyboardInterrupt:
        import sys
        sys.exit()
