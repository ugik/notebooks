from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
import backtrader as bt # Import the backtrader platfor


class RSIStrategy(bt.Strategy):

    params = (
        ('verbose', False),
        ('maperiod', None),
        ('quantity', None),
        ('upper', 70),         # upper threshold
        ('lower', 30),         # lower threshold
        ('stopLoss', 0.00)          # stop loss %
    )


    def __init__(self):

        self.dataclose = self.datas[0].close
        self.order = None
        self.order_stopLoss = None
        self.buyprice = None
        self.buycomm = None
        self.amount = None

        # Add a MovingAverageSimple indicator
        self.rsi = bt.indicators.RSI_SMA(self.datas[0], period=self.params.maperiod)


    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm

                if self.params.verbose:
                    print('BOUGHT @price: {:.2f} {}'.format(order.executed.price, bt.num2date(order.executed.dt)))
                if self.params.stopLoss:
                    if self.params.stopLoss > 0:
                        stop_price = order.executed.price * (1 - self.params.stopLoss)
                        self.order_stopLoss = self.sell(exectype=bt.Order.Stop, price=stop_price)
                        if self.params.verbose:
                            print('  STOP @price: {:.2f}'.format(stop_price))
                    else:
                        # trailing stop specified % under executed price
                        self.order_stopLoss = self.sell(exectype=bt.Order.StopTrail, trailpercent=0-self.params.stopLoss)
                        self.order_stopLoss.addinfo(ordername="STOPLONG")
                        if self.params.verbose:
                            print('  STOP TRAILING')

            else:
                if not self.position:  # we left the market
                    self.broker.cancel(self.order_stopLoss)
                    self.order_stopLoss = None
                    if self.params.verbose:
                        print('SOLD @price: {:.2f} cost: {:.2f} comm: {:.2f} {}'.format(order.executed.price, order.executed.value, order.executed.comm, bt.num2date(order.executed.dt)))

        self.order = None


    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        if self.params.verbose:
            print('PROFIT, GROSS %.2f, NET %.2f' % (trade.pnl, trade.pnlcomm))
            print('_______________________________________________')



    def next(self):

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            if self.rsi < self.params.lower:

                # Keep track of the created order to avoid a 2nd order
                self.amount = (self.broker.getvalue() * self.params.quantity) / self.dataclose[0]
                self.order = self.buy()

        else:
            # Already in the market ... we might sell
            if self.rsi > self.params.upper:

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()



# ______________________ End Strategy Classes



def timeFrame(datapath):
    """
    Select the write compression and timeframe.
    """
    sepdatapath = datapath[5:-4].split(sep='-') # ignore name file 'data/' and '.csv'
    tf = sepdatapath[3]

    if tf == '1m':
        compression = 1
        timeframe = bt.TimeFrame.Minutes
    else:
        print('dataframe not recognized')
        exit()

    return compression, timeframe


def getWinLoss(analyzer):
    return analyzer.won.total, analyzer.lost.total, analyzer.pnl.net.total


def getSQN(analyzer):
    return round(analyzer.sqn,2)



def runbacktest(datapath, start, end, period, strategy, \
                upper=70, lower=30, commission_val=None, portofolio=10000.0, stake_val=1, quantity=0.01, stopLoss=0.0, plt=False):

    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a FixedSize sizer according to the stake
    cerebro.addsizer(bt.sizers.FixedSize, stake=stake_val) # Multiply the stake by X

    cerebro.broker.setcash(portofolio)

    if commission_val:
        cerebro.broker.setcommission(commission=commission_val/100)

    # Add a strategy
    if strategy == 'SMA':
        cerebro.addstrategy(SMAStrategy, maperiod=period, quantity=quantity, stopLoss=stopLoss, upper=upper, lower=lower)
    elif strategy == 'RSI':
        cerebro.addstrategy(RSIStrategy, maperiod=period, quantity=quantity, stopLoss=stopLoss, upper=upper, lower=lower)
    else :
        print('no strategy')
        exit()

    compression, timeframe = timeFrame(datapath)

    # Create a Data Feed
    data = bt.feeds.GenericCSVData(
        dataname = datapath,
        dtformat = 2, 
        compression = compression, 
        timeframe = timeframe,
        fromdate = datetime.datetime.strptime(start, '%Y-%m-%d'),
        todate = datetime.datetime.strptime(end, '%Y-%m-%d'),
        reverse = False)


    # Add the Data Feed to Cerebro
    cerebro.adddata(data)


    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="ta")
    cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")

#    try:     # convenience try/exception block
    if True:
        strat = cerebro.run()
        stratexe = strat[0]

        try:
            totalwin, totalloss, pnl_net = getWinLoss(stratexe.analyzers.ta.get_analysis())
        except KeyError:
            totalwin, totalloss, pnl_net = 0, 0, 0

        sqn = getSQN(stratexe.analyzers.sqn.get_analysis())

        if plt:
            cerebro.plot()

        return cerebro.broker.getvalue(), totalwin, totalloss, pnl_net, sqn

 #   except Exception as e:         # handle unexpected errors gracefully
 #       print('Error:', str(e))
 #       return 0, 0, 0, 0, 0

