import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from tqsdk import TqApi, TqAuth, TqSim, TqBacktest, TargetPosTask, BacktestFinished
from tqsdk.tafunc import ma
import sys
import ctypes

def win_getpass(prompt="Password: "):
    if sys.platform == 'win32':
        print(prompt, end='', flush=True)
        password = ""
        while True:
            ch = ctypes.windll.msvcrt._getwch()
            if ch == 13:
                print()
                break
            elif ch == 8:
                if password:
                    password = password[:-1]
                    print("\b \b", end='', flush=True)
            elif ch == 3:
                raise KeyboardInterrupt
            elif 32 <= ch <= 126:
                password += chr(ch)
                print('*', end='', flush=True)
        return password
    else:
        import getpass
        return getpass.getpass(prompt)

def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d").date()

print("=== 策略参数配置 ===")
username = input("请输入账户名: ")
password = win_getpass("请输入账户密码: ")
symbol = input("请输入合约代码 (如 SHFE.cu2604): ")
start_dt_str = input("请输入回测开始日期 (格式: YYYY-MM-DD): ")
end_dt_str = input("请输入回测结束日期 (格式: YYYY-MM-DD): ")
slow_ma = int(input("请输入慢均线周期 (如 20): "))
fast_ma = int(input("请输入快均线周期 (如 5): "))
stop_loss = float(input("请输入止损比例 (如 0.02 表示2%): "))
take_profit = float(input("请输入止盈比例 (如 0.03 表示3%): "))

start_dt = parse_date(start_dt_str)
end_dt = parse_date(end_dt_str)

api = None
try:
    acc = TqSim()
    api = TqApi(acc, backtest=TqBacktest(start_dt=start_dt, end_dt=end_dt), auth=TqAuth(username, password))
    #策略代码
    data_length = slow_ma + 2  # k线数据长度
    # 日线的duration_seconds参数为: 24*60*60
    klines = api.get_kline_serial(symbol, duration_seconds=24*60*60, data_length=data_length)
    # 创建任务
    target_pos = TargetPosTask(api, symbol)
    # 在循环外定义变量，用于记录开仓价格和方向
    entry_price = None
    entry_direction = None  # 'long' 或 'short'

    while True:
        api.wait_update()
        try:
            quote = api.get_quote(symbol)

            # 风控检查
            if entry_price is not None and entry_direction is not None:
                current_price = quote.last_price
                if np.isnan(current_price):
                    continue   # 无最新价则跳过

                if entry_direction == 'long':
                    pnl_ratio = (current_price - entry_price) / entry_price
                    if pnl_ratio <= -stop_loss:
                        print(f"触发多头止损，平仓 | 价格: {current_price:.2f} | 盈亏: {pnl_ratio:.2%}")
                        target_pos.set_target_volume(0)
                        entry_price = None
                        entry_direction = None
                    elif pnl_ratio >= take_profit:
                        print(f"触发多头止盈，平仓 | 价格: {current_price:.2f} | 盈亏: {pnl_ratio:.2%}")
                        target_pos.set_target_volume(0)
                        entry_price = None
                        entry_direction = None
                elif entry_direction == 'short':
                    pnl_ratio = (entry_price - current_price) / entry_price
                    if pnl_ratio <= -stop_loss:
                        print(f"触发空头止损，平仓 | 价格: {current_price:.2f} | 盈亏: {pnl_ratio:.2%}")
                        target_pos.set_target_volume(0)
                        entry_price = None
                        entry_direction = None
                    elif pnl_ratio >= take_profit:
                        print(f"触发空头止盈，平仓 | 价格: {current_price:.2f} | 盈亏: {pnl_ratio:.2%}")
                        target_pos.set_target_volume(0)
                        entry_price = None
                        entry_direction = None

            # 信号判断
            if api.is_changing(klines.iloc[-1], "datetime"):
                short_avg = ma(klines["close"], fast_ma)
                long_avg = ma(klines["close"], slow_ma)

                # 做空信号
                if long_avg.iloc[-2] < short_avg.iloc[-2] and long_avg.iloc[-1] > short_avg.iloc[-1]:
                    # 确保开仓价有效
                    if np.isnan(quote.bid_price1):
                        continue
                    target_pos.set_target_volume(-3)
                    entry_price = quote.bid_price1
                    entry_direction = 'short'
                    print(f"均线下穿，做空，entry_price：{entry_price:.2f}")

                # 做多信号
                if short_avg.iloc[-2] < long_avg.iloc[-2] and short_avg.iloc[-1] > long_avg.iloc[-1]:
                    if np.isnan(quote.ask_price1):
                        continue
                    target_pos.set_target_volume(3)
                    entry_price = quote.ask_price1
                    entry_direction = 'long'
                    print(f"均线上穿，做多，entry_price：{entry_price:.2f}")

        except (ValueError, KeyError, IndexError) as e:
            print(f"处理k线数据时出错: {e}")
    
except BacktestFinished as e:
    api.close()
    result = acc.tqsdk_stat
    if result:
        print({k: float(v) if hasattr(v, 'item') else (None if str(v) == 'nan' else v) for k, v in result.items()})
    input("\n回测结束，按回车键退出...")

