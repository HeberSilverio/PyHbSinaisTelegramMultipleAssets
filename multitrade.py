#! /usr/bin/python3
# -*- coding: utf-8 -*-
import config
from binance.client import Client
import sys
import numpy as np
import pandas as pd
import asyncio
from binance import AsyncClient, BinanceSocketManager
import telegramBot as tlg
import talib
from datetime import datetime

TIME_INTERVAL ='5m'

RSI_PERIOD = 7
RSI_OVERBOUGHT = 90
RSI_OVERSOLD = 20
RSIS_OVERBOUGHT = 90
RSIS_OVERSOLD = 20

def binanceDataFrame( klines):
   # df = pd.DataFrame(klines.reshape(-1,12),dtype=float, columns = ('Open Time',
   #                                                                 'Open',
   #                                                                 'High',
   #                                                                 'Low',
   #                                                                 'Close',
   #                                                                 'Volume',
   #                                                                 'Close time',
   #                                                                 'Quote asset volume',
   #                                                                 'Number of trades',
   #                                                                 'Taker buy base asset volume',
   #                                                                 'Taker buy quote asset volume',
   #                                                                 'Ignore'))
   # df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
   df = pd.DataFrame(klines.reshape(-1,12),dtype=float, columns=['T', 
      'open', 
      'high', 
      'low', 
      'close', 
      'V', 
      'CT', 
      'QV', 
      'N', 
      'TB', 
      'TQ', 
      'I'])
   df['T'] = pd.to_datetime(df['T'], unit='ms')
   return df

def get_timeInterval(ti,Client):

   if ti == '1m':
      return Client.KLINE_INTERVAL_1MINUTE
   elif ti == '5m':
      return Client.KLINE_INTERVAL_5MINUTE
   elif ti == '1h':
      return Client.KLINE_INTERVAL_1HOUR
   elif ti == '4h':
      return Client.KLINE_INTERVAL_4HOUR
   elif ti == '1d':
      return Client.KLINE_INTERVAL_1DAY
   else:
      return Client.KLINE_INTERVAL_15MINUTE
   
def removeExcedent(df,qtmanter):
   if len(df) > qtmanter:
      qt2remove = len(df) - qtmanter
      df.drop(index=df.index[:qt2remove],
      axis=0, 
      inplace=True)
   return df

def createframe(msg):
   df = pd.DataFrame([msg['data']])
   return (df)

def on_message(message):
   global klines_df, closes

   TRADE_SYMBOL = message['s'][0]
   candle = message['k'][0]
   close = candle['c']

   is_candle_closed = candle['x']

   
   # se candle esta fechado
   if is_candle_closed:
      # print(TRADE_SYMBOL+" \t"+str(candle['x'])+"\t"+str(datetime.fromtimestamp(int(candle['T'])/1000))) 

      df2 = pd.DataFrame({"T": [datetime.fromtimestamp(int(candle['T'])/1000)],
               "open":[float(candle['o'])],
               "high":[float(candle['h'])],
               "low": [float(candle['l'])],
               "close":[float(candle['c'])],
               "V": [float(candle['v'])    ],
               "CT": [0],
               "QV":[float(candle['q'])],
               "N": [0],
               "TB":[ 0],
               "TQ": [0],
               "I":[0]}
               )
      
      klines_df[TRADE_SYMBOL] = pd.concat([klines_df[TRADE_SYMBOL], df2])

      klines_df[TRADE_SYMBOL] = removeExcedent(klines_df[TRADE_SYMBOL],50)

      closes[TRADE_SYMBOL].append(float(close))

      np_closes = np.array(closes[TRADE_SYMBOL])
      
      #Define data e hora atuais
      data_e_hora_atuais = datetime.now()
      data_e_hora_em_texto = data_e_hora_atuais.strftime('%d/%m/%Y - %Hh:%Mm') 
      
      print("--------------------------------------")
      print("CRYPTO         :\t",TRADE_SYMBOL)
      print("Closed value   :\t",format(float(close),'.6f'))
      
      #INDICADORES
      if len(closes[TRADE_SYMBOL]) > 26:
         macd, macdsignal, macdhist = talib.MACD(np_closes, fastperiod=12, slowperiod=26, signalperiod=9)
         
      if len(closes[TRADE_SYMBOL]) > 21:
         fastk, fastd  = talib.STOCHRSI(np_closes,timeperiod=21, fastk_period=21, fastd_period=3, fastd_matype=3)
      
      rsi = talib.RSI(np_closes, RSI_PERIOD)
      last_rsi = rsi[-1]

      # Bandas de Bollinger
      if len(closes[TRADE_SYMBOL]) > 19 :
         upper, middle, lower = talib.BBANDS(np_closes, 21, 3, 3)
         # upperband, middleband, lowerband = talib.BBANDS(np_closes, timeperiod=21, nbdevup=2, nbdevdn=2, matype=0)
         # Remova o primeiro elemento
         # np_closes = np_closes[1:]
         BBSuperior = upper[-1]
         BBMedia = middle[-1]
         BBInferior = lower[-1]
         
         
      # Se máxima maior que banda superior
      if (format(float(candle['h']),'.8f') > format(float(BBSuperior),'.8f')):
            telegramBot.send_msg("\n -------------------------------")
            telegramBot.send_msg("=== *VENDER {}* ===".format(TRADE_SYMBOL)
                  +"\n♨️Máxima *ACIMA* da Bollinger ♨️"
                  +"\n TIME  " + data_e_hora_em_texto 
                  +"\n*Tempo Gráfico: {}*".format(TIME_INTERVAL)
                  +"\nBollinger Superior......."+str(format(float(BBSuperior),'.5f'))
                  +"\n*Máxima*....................."+str(format(float(close),'.5f'))
                  +"\n*VOLUME*....................."+str(format(float(candle['v']),'.5f'))
                  +"\n*Nº trade*....................."+str(format(float(candle['n']),'.5f')))
                  
            
         # Se mínima menor que banda inferior
      if (format(float(candle['l']),'.8f') < format(float(BBInferior),'.8f')):
            telegramBot.send_msg("\n -------------------------------")
            telegramBot.send_msg("=== *COMPRAR {}* ===".format(TRADE_SYMBOL)
                  +"\n 🟢💸 *Mínima *ABAIXO* da Bollinger* 💸🟢"
                  +"\n TIME  " + data_e_hora_em_texto 
                  +"\n*Tempo Gráfico: {}*".format(TIME_INTERVAL)            
                  +"\nBollinger Inferior..........."+str(format(float(BBInferior),'.6f'))
                  +"\nFechamento..................."+str(format(float(candle['l']),'.6f'))
                  +"\n*VOLUME*....................."+str(format(float(candle['v']),'.5f'))
                  +"\n*Nº trade*....................."+str(format(float(candle['n']),'.5f')))
            
         
         # Se fechamento entre a media central
      if ((format(float(candle['h']),'.8f') > format(float(BBMedia),'.8f')) and (format(float(candle['l']),'.8f') < format(float(BBMedia),'.8f'))):
            telegramBot.send_msg("\n -------------------------------")
            telegramBot.send_msg("== *LATERALIDADE {}* ==".format(TRADE_SYMBOL)
                  +"\n🟡  🟡  🟡  🟡  🟡  🟡"
                  +"\nTIME  " + data_e_hora_em_texto 
                  +"\n*Tempo Gráfico: {}*".format(TIME_INTERVAL) 
                  +"\nBB Central......"+str(format(float(BBMedia),'.6f'))
                  +"\n*Fechamento*......"+str(format(float(close),'.6f'))
                  +"\nFechamento próximo a media central"
                  +"\n*VOLUME*....................."+str(format(float(candle['v']),'.5f'))
                  +"\n*Nº trade*....................."+str(format(float(candle['n']),'.5f'))
                  +"\n*VOLUME*....................."+str(format(float(candle['v'][-1]),'.5f')))
                  
                              
      # ### Que interessa
      # if format(float(candle['c']),'.8f') < format(float(BBInferior),'.8f'):
      #       telegramBot.send_msg("\n -------------------------------")
      #       telegramBot.send_msg("=== *COMPRAR {}* ===".format(TRADE_SYMBOL)
      #             +"\n 🟢  🟢  🟢  🟢  🟢  🟢  🟢"
      #             +"\nTIME  " + data_e_hora_em_texto 
      #             +"\nTempo Gráfico: " +str(TIME_INTERVAL)
      #             +"\n*Fechou ABAIXO da Bollinger*"                
      #             +"\nVALOR.............."+str(format(float(candle['c']),'.6f'))
      #             +"\nBBInferior.............."+str(format(float(BBInferior),'.6f')))
         
            
      # elif format(float(candle['c']),'.8f') > format(float(BBSuperior),'.8f'):                             
      #    telegramBot.send_msg("=== *VENDER {}* ===".format(TRADE_SYMBOL)
      #          +"\n 🔴  🔴  🔴  🔴  🔴  🔴"
      #          +"\nTIME  " + data_e_hora_em_texto 
      #          +"\nTempo Gráfico: " +str(TIME_INTERVAL)
      #          +"\n*Fechou ACIMA da Bollinger*"
      #          +"\nBBSuperior.............."+str(format(float(BBSuperior),'.6f'))
      #          +"\nValor............"+str(format(float(candle['c']),'.6f'))) 
         
            
async def main():
   #inicializa o cliente
   client = await AsyncClient.create()

   # Instancie um BinanceSocketManager, passando o cliente que você instanciou
   bm = BinanceSocketManager(client)

   # Crie um soquete combinando vários fluxos.
   ms = bm.multiplex_socket(multi)

   # criar ouvinte usando assíncrono com
   async with ms as tscm:
      while True:
         res = await tscm.recv()
         if res:
               df = createframe(res)
               on_message(df)
                
if __name__ == "__main__":
   # Configuração do telegram
   telegramBot = tlg.BotTelegram(config.TOKEN,config.CHAT_ID)
   telegramBot.send_msg("=== Inicio do bot PyHbSinais ===")
   
   # Mostra status da conta
   client = Client(config.API_KEY, config.API_SECRET)
   status = client.get_account_status()
   info = client.get_account()
   balance = client.get_asset_balance(asset='USDT')
   telegramBot.send_msg("Status da conta:" + " " + str(status).replace("'data': ",""))
                          
   

   if len(sys.argv) > 1:
      relevant = config.SYMBOLS
   else:
      info = client.get_exchange_info()
      symbols = [x['symbol'] for x in info['symbols']]
      exclude = ['UP','DOWN','BEAR','BULL']
      non_lev = [symbol for symbol in symbols if all(excludes not in symbol for excludes in exclude)]
      relevant = [symbol  for symbol in non_lev if symbol.endswith('USDT')]
    
    
   # Array multi percorre relevant e adiciona intervalo 
   multi = [i.lower() + '@kline_'+TIME_INTERVAL for i in relevant]

   # dicionario de varias moedas
   klines = dict()
   closes = dict()
   klines_df = dict()
   klines_np = dict()

   for i in relevant:
      print("Carregando dados históricos de "+i)
      telegramBot.send_msg("Carregando dados históricos de "+i)
      klines[i] = client.get_historical_klines(i, get_timeInterval(TIME_INTERVAL,client), "1 day ago UTC")

      closes[i] = []

      for candles in range(len(klines[i])-1):
         closes[i].append(float(klines[i][candles][4]))
      
      klines_np[i] = np.array(klines[i])

      klines_df[i] = binanceDataFrame(klines_np[i])

      klines_df[i] = klines_df[i][:-1]
      
      klines_df[i] = removeExcedent(klines_df[i],50)

      # print(klines_df[i],len(klines_df[i]))
      
   print("Monitorando....")

   loop = asyncio.get_event_loop()
   loop.run_until_complete(main())