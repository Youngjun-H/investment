import pandas as pd
import mplfinance as mpf
from pykrx import stock
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'  # macOS용 한글 폰트
plt.rcParams['axes.unicode_minus'] = False   # 마이너스 기호 깨짐 방지
plt.rcParams['figure.titlesize'] = 20

def get_ticker_by_name(name):
    """종목명을 입력받아 종목코드를 찾아 반환합니다."""
    # pykrx의 모든 종목 티커를 가져와서 딕셔너리로 만듭니다. {종목명: 종목코드}
    ticker_map = {stock.get_market_ticker_name(ticker): ticker for ticker in stock.get_market_ticker_list()}
    
    ticker = ticker_map.get(name)
    if ticker:
        print(f"'{name}'에 해당하는 종목코드는 '{ticker}'입니다.")
        return ticker
    else:
        # 혹시 종목코드를 직접 입력했을 경우를 대비
        if name in stock.get_market_ticker_list():
            return name
        print(f"'{name}'에 해당하는 종목을 찾을 수 없습니다.")
        return None

def generate_trade_chart(ticker, stock_name, buy_date_str, buy_price, sell_date_str, sell_price):
    """
    매매 정보를 입력받아 캔들스틱 차트를 그리고 이미지 파일로 저장합니다.
    """
    try:
        # 1. 날짜 형식 변환 및 차트 기간 설정
        buy_date = datetime.strptime(buy_date_str, '%Y%m%d')
        sell_date = datetime.strptime(sell_date_str, '%Y%m%d')

        # 차트 기간을 오늘을 기준으로 1년 전부터로 설정 (매매기간과 무관)
        today = datetime.now()
        start_date = today - timedelta(days=180)  # 1년 전
        end_date = today
        
        # 날짜를 pykrx가 요구하는 'YYYYMMDD' 형식의 문자열로 변환
        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')

        print(f"차트 기간: {start_date_str}부터 {end_date_str}까지 (오늘 기준 1년)")
        print(f"매매 기간: {buy_date_str} ~ {sell_date_str}")

        # 2. pykrx를 이용해 해당 기간의 OHLCV(시가, 고가, 저가, 종가, 거래량) 데이터 가져오기
        # 수정된 주가 사용 (배당, 액면분할, 유무상증자 등 반영)
        df = stock.get_market_ohlcv(start_date_str, end_date_str, ticker, adjusted=True)

        if df.empty:
            print("해당 기간의 주가 데이터를 가져올 수 없습니다. 날짜나 종목코드를 확인해주세요.")
            return

        # 디버그: 컬럼명 확인
        print(f"DataFrame 컬럼명: {df.columns.tolist()}")
        print(f"DataFrame 샘플:\n{df.head()}")

        # 3. pykrx의 한글 컬럼명을 mplfinance가 요구하는 영문 컬럼명으로 변경
        column_mapping = {
            '시가': 'Open',
            '고가': 'High', 
            '저가': 'Low',
            '종가': 'Close',
            '거래량': 'Volume'
        }
        
        # 컬럼명 변경
        df = df.rename(columns=column_mapping)
        
        print(f"변경된 DataFrame 컬럼명: {df.columns.tolist()}")

        # 4. 매수/매도 지점 표시를 위한 데이터 준비
        #    - 차트의 날짜 인덱스와 동일한 길이를 가지는 Series 생성
        #    - 매수/매도일에만 가격을 표시하고 나머지 날짜는 NaN(결측치)으로 채움
        buy_markers = pd.Series(float('nan'), index=df.index)
        sell_markers = pd.Series(float('nan'), index=df.index)
        
        # loc를 사용하여 정확한 날짜에 가격 정보 삽입
        if buy_date in df.index:
            buy_markers.loc[buy_date] = buy_price
        
        if sell_date in df.index:
            sell_markers.loc[sell_date] = sell_price

        # 5. 지수이동평균선 계산 및 추가
        # 10일 지수이동평균선 (빨간색)
        ema_10 = df['Close'].ewm(span=10).mean()
        # 60일 지수이동평균선 (파란색)
        ema_60 = df['Close'].ewm(span=60).mean()
        
        # 6. mplfinance를 사용하여 차트 그리기
        #    - make_addplot을 사용하여 매수/매도 마커와 이동평균선 추가
        add_plots = [
            mpf.make_addplot(buy_markers, type='scatter', marker='^', color='red', markersize=150, label='Buy'),
            mpf.make_addplot(sell_markers, type='scatter', marker='v', color='blue', markersize=150, label='Sell'),
            mpf.make_addplot(ema_10, color='red', width=1.5, label='EMA 10'),
            mpf.make_addplot(ema_60, color='blue', width=1.5, label='EMA 60'),
        ]

        # 차트 파일명 설정
        filename = f"{stock_name}({ticker})_{buy_date_str}-{sell_date_str}_trade.png"

        # 1. 나만의 색상 조합 정의 (부드러운 파란색/회색 톤)
        my_colors = mpf.make_marketcolors(
            up='#D94848',        # 상승 캔들: 선명한 빨간색
            down='#4985D9',      # 하락 캔들: 선명한 파란색
            edge='inherit',      # 캔들 테두리는 몸통 색을 따름
            wick='inherit',      # 캔들 꼬리 색도 몸통 색을 따름
            volume={'up': '#D94848', 'down': '#4985D9'} # 거래량 색상 통일
        )

        # 2. 나만의 스타일 생성
        # 한글 폰트가 깨질 경우를 대비해 폰트 설정 추가
        rc_params = {'font.family': 'AppleGothic'} 
        my_style = mpf.make_mpf_style(
            base_mpf_style='yahoo', # 어두운 배경을 기반으로 시작
            marketcolors=my_colors,
            facecolor='#EAEAEA',              # 차트 배경: 연한 회색
            gridcolor='#D9D9D9',              # 그리드(격자) 색상
            gridstyle='--',                   # 그리드 스타일: 점선
            rc=rc_params                      # 한글 폰트 설정 적용
        )

        # 차트 생성 및 저장
        fig, axes = mpf.plot(df,
                type='candle',
                style=my_style,
                volume=True,
                title=f'{stock_name} ({ticker}) Trading Log',
                addplot=add_plots,
                ylabel='가격 (원)',
                ylabel_lower='거래량',
                figsize=(16, 8),
                returnfig=True
            )

        # 차트 상단 여백을 수동으로 조절하여 제목 공간 확보
        fig.set_facecolor('#EAEAEA')
        fig.subplots_adjust(top=1.0)

        # 수동으로 조정한 레이아웃을 포함하여 파일로 저장
        fig.savefig(filename, bbox_inches='tight')

        print(f"\n✅ 차트가 성공적으로 '{filename}' 파일로 저장되었습니다.")

    except Exception as e:
        print(f"\n❌ 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    # --- 사용자 입력 ---
    # input_stock_name = input("종목명 또는 종목코드를 입력하세요 (예: 삼성전자 또는 005930): ")
    # input_buy_date = input("매수 날짜를 입력하세요 (예: 20240115): ")
    # input_buy_price = float(input("매수 가격을 입력하세요 (예: 75000): "))
    # input_sell_date = input("매도 날짜를 입력하세요 (예: 20240320): ")
    # input_sell_price = float(input("매도 가격을 입력하세요 (예: 81000): "))
    input_stock_name = "삼성전자"
    input_buy_date = "20250219"
    input_buy_price = 58000
    input_sell_date = "20250625"
    input_sell_price = 61000
    
    print("\n차트 생성을 시작합니다...")
    
    # 종목명으로 종목코드 찾기
    ticker_code = get_ticker_by_name(input_stock_name)
    
    if ticker_code:
        # 차트 생성 함수 호출
        generate_trade_chart(
            ticker=ticker_code,
            stock_name=stock.get_market_ticker_name(ticker_code), # 종목코드로 정확한 종목명 다시 가져오기
            buy_date_str=input_buy_date,
            buy_price=input_buy_price,
            sell_date_str=input_sell_date,
            sell_price=input_sell_price
        )