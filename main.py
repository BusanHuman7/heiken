import os
import requests
import pandas as pd
import ccxt

# ==========================================
# 1. 설정 (업비트 종목 및 시간대)
# ==========================================
SYMBOL = 'BTC/KRW'  # 업비트 원화 마켓 (예: ETH/KRW, XRP/KRW 등으로 변경 가능)
TIMEFRAME = '1h'

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_heikin_ashi_data(symbol, timeframe):
    """업비트에서 1시간봉 OHLCV 데이터를 수집 후 하이킨아시 계산"""
    exchange = ccxt.upbit({'enableRateLimit': True})
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=50)
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # 업비트 기본 UTC 시간을 한국 시간(KST, +9시간)으로 변환
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=9)

    # 하이킨아시(Heiken Ashi) 계산
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = [(df['open'].iloc[0] + df['close'].iloc[0]) / 2]
    
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha_close.iloc[i-1]) / 2)
        
    df['ha_close'] = ha_close
    df['ha_open'] = ha_open
    df['ha_high'] = df[['high', 'ha_open', 'ha_close']].max(axis=1)
    df['ha_low'] = df[['low', 'ha_open', 'ha_close']].min(axis=1)

    return df

def send_telegram_message(message):
    """텔레그램 메시지 발송"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("에러: TELEGRAM_TOKEN 또는 CHAT_ID 설정이 누락되었습니다.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    response = requests.post(url, json=payload)
    print(f"Telegram API Response: {response.status_code}")

def main():
    try:
        df = get_heikin_ashi_data(SYMBOL, TIMEFRAME)
        
        # 가장 최근에 '완성된' 1시간 봉 (직전 봉: index -1)
        last_candle = df.iloc[-1]
        current_candle = df.iloc[-1]

        ha_open = last_candle['ha_open']
        ha_close = last_candle['ha_close']
        current_price = current_candle['close']

        # 양봉 / 음봉 판별
        is_bullish = ha_close >= ha_open
        status_emoji = "🟢 **양봉 (상승)**" if is_bullish else "🔴 **음봉 (하락)**"
        
        # 메시지 구성 (원화 표시 및 KST 적용)
        candle_time = last_candle['datetime'].strftime('%Y-%m-%d %H:00 (KST)')
        
        message = (
            f"📊 **[{SYMBOL}] 업비트 1시간 하이킨아시 리포트**\n\n"
            f"⏰ **기준 시간:** `{candle_time}`\n"
            f"🕯️ **하이킨아시 상태:** {status_emoji}\n"
            f"💰 **현재가:** `₩{current_price:,.0f}`\n"
            f"📈 **HA 시가:** `₩{ha_open:,.0f}`\n"
            f"📉 **HA 종가:** `₩{ha_close:,.0f}`\n\n"
            f"💡 *자동화 시스템에 의해 매시 정각 모니터링됩니다.*"
        )

        send_telegram_message(message)
        print("업비트 기준 메시지 전송 완료!")

    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == '__main__':
    main()
