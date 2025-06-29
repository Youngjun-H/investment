import pandas as pd
import mplfinance as mpf
from pykrx import stock
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import logging
import os
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
import warnings

# 경고 메시지 무시
warnings.filterwarnings('ignore')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_chart.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ChartConfig:
    """차트 설정을 위한 데이터 클래스"""
    # 차트 기간 설정
    CHART_PERIOD_DAYS: int = 180
    
    # 이동평균선 설정
    EMA_PERIODS: Tuple[int, int] = (10, 60)
    EMA_COLORS: Tuple[str, str] = ('#FF4444', '#4444FF')
    
    # 차트 스타일 설정
    CHART_STYLE: str = 'yahoo'
    BACKGROUND_COLOR: str = '#EAEAEA'
    GRID_COLOR: str = '#D9D9D9'
    GRID_STYLE: str = '--'
    
    # 캔들 색상 설정
    CANDLE_UP_COLOR: str = '#D94848'
    CANDLE_DOWN_COLOR: str = '#4985D9'
    
    # 차트 크기 설정
    FIGURE_SIZE: Tuple[int, int] = (16, 8)
    DPI: int = 150
    
    # 마커 설정
    BUY_MARKER: str = '^'
    SELL_MARKER: str = 'v'
    MARKER_SIZE: int = 150
    BUY_COLOR: str = '#FF0000'
    SELL_COLOR: str = '#0000FF'

class FontManager:
    """폰트 관리 클래스"""
    
    @staticmethod
    def setup_korean_font() -> None:
        """한글 폰트 설정"""
        try:
            # macOS용 한글 폰트 설정
            plt.rcParams['font.family'] = 'AppleGothic'
            plt.rcParams['axes.unicode_minus'] = False
            
            # 폰트 설정 확인
            font_path = fm.findfont(fm.FontProperties(family='AppleGothic'))
            if font_path.endswith('DejaVuSans.ttf'):
                logger.warning("AppleGothic 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
                plt.rcParams['font.family'] = 'DejaVu Sans'
                
        except Exception as e:
            logger.error(f"폰트 설정 중 오류 발생: {e}")
            plt.rcParams['font.family'] = 'DejaVu Sans'

class StockDataManager:
    """주식 데이터 관리 클래스"""
    
    def __init__(self):
        self._ticker_cache: Dict[str, str] = {}
        self._load_ticker_cache()
    
    def _load_ticker_cache(self) -> None:
        """종목코드 캐시 로드"""
        try:
            ticker_list = stock.get_market_ticker_list()
            self._ticker_cache = {
                stock.get_market_ticker_name(ticker): ticker 
                for ticker in ticker_list
            }
            logger.info(f"종목코드 캐시 로드 완료: {len(self._ticker_cache)}개")
        except Exception as e:
            logger.error(f"종목코드 캐시 로드 실패: {e}")
    
    def get_ticker_by_name(self, name: str) -> Optional[str]:
        """종목명으로 종목코드 조회"""
        try:
            # 캐시에서 조회
            ticker = self._ticker_cache.get(name)
            if ticker:
                logger.info(f"종목 '{name}' -> 종목코드 '{ticker}'")
                return ticker
            
            # 직접 종목코드 입력인 경우
            if name in stock.get_market_ticker_list():
                logger.info(f"직접 입력된 종목코드: {name}")
                return name
            
            logger.error(f"종목 '{name}'을 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            logger.error(f"종목코드 조회 중 오류: {e}")
            return None
    
    def get_stock_data(self, ticker: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """주식 데이터 조회"""
        try:
            logger.info(f"주식 데이터 조회 중: {ticker} ({start_date} ~ {end_date})")
            
            # 수정된 주가 데이터 조회
            df = stock.get_market_ohlcv(start_date, end_date, ticker, adjusted=True)
            
            if df.empty:
                logger.error("조회된 데이터가 없습니다.")
                return None
            
            # 컬럼명 변환
            column_mapping = {
                '시가': 'Open',
                '고가': 'High', 
                '저가': 'Low',
                '종가': 'Close',
                '거래량': 'Volume'
            }
            df = df.rename(columns=column_mapping)
            
            logger.info(f"데이터 조회 완료: {len(df)}개 행")
            return df
            
        except Exception as e:
            logger.error(f"주식 데이터 조회 중 오류: {e}")
            return None

class ChartStyleManager:
    """차트 스타일 관리 클래스"""
    
    def __init__(self, config: ChartConfig):
        self.config = config
    
    def create_custom_style(self):
        """커스텀 차트 스타일 생성"""
        try:
            # 마켓 컬러 설정
            market_colors = mpf.make_marketcolors(
                up=self.config.CANDLE_UP_COLOR,
                down=self.config.CANDLE_DOWN_COLOR,
                edge='inherit',
                wick='inherit',
                volume={
                    'up': self.config.CANDLE_UP_COLOR, 
                    'down': self.config.CANDLE_DOWN_COLOR
                }
            )
            
            # 스타일 생성
            style = mpf.make_mpf_style(
                base_mpf_style=self.config.CHART_STYLE,
                marketcolors=market_colors,
                facecolor=self.config.BACKGROUND_COLOR,
                gridcolor=self.config.GRID_COLOR,
                gridstyle=self.config.GRID_STYLE,
                rc={'font.family': 'AppleGothic'}
            )
            
            logger.info("커스텀 차트 스타일 생성 완료")
            return style
            
        except Exception as e:
            logger.error(f"차트 스타일 생성 중 오류: {e}")
            return mpf.make_mpf_style()

class TechnicalIndicator:
    """기술적 지표 계산 클래스"""
    
    @staticmethod
    def calculate_ema(data: pd.Series, periods: Tuple[int, int]) -> Tuple[pd.Series, pd.Series]:
        """지수이동평균선 계산"""
        try:
            ema_short = data.ewm(span=periods[0]).mean()
            ema_long = data.ewm(span=periods[1]).mean()
            
            logger.info(f"EMA 계산 완료: {periods[0]}일, {periods[1]}일")
            return ema_short, ema_long
            
        except Exception as e:
            logger.error(f"EMA 계산 중 오류: {e}")
            return pd.Series(), pd.Series()
    
    @staticmethod
    def create_trade_markers(df: pd.DataFrame, buy_date: datetime, 
                           buy_price: float, sell_date: datetime, 
                           sell_price: float) -> Tuple[pd.Series, pd.Series]:
        """매매 마커 생성"""
        try:
            buy_markers = pd.Series(float('nan'), index=df.index)
            sell_markers = pd.Series(float('nan'), index=df.index)
            
            if buy_date in df.index:
                buy_markers.loc[buy_date] = buy_price
            
            if sell_date in df.index:
                sell_markers.loc[sell_date] = sell_price
            
            logger.info("매매 마커 생성 완료")
            return buy_markers, sell_markers
            
        except Exception as e:
            logger.error(f"매매 마커 생성 중 오류: {e}")
            return pd.Series(), pd.Series()

class ChartGenerator:
    """차트 생성 클래스"""
    
    def __init__(self, config: ChartConfig):
        self.config = config
        self.data_manager = StockDataManager()
        self.style_manager = ChartStyleManager(config)
        self.indicator = TechnicalIndicator()
        
        # 폰트 설정
        FontManager.setup_korean_font()
    
    def generate_trade_chart(self, stock_name: str, buy_date_str: str, 
                           buy_price: float, sell_date_str: str, 
                           sell_price: float) -> bool:
        """매매 차트 생성"""
        try:
            logger.info("차트 생성 시작")
            
            # 1. 종목코드 조회
            ticker = self.data_manager.get_ticker_by_name(stock_name)
            if not ticker:
                return False
            
            # 2. 날짜 설정
            buy_date = datetime.strptime(buy_date_str, '%Y%m%d')
            sell_date = datetime.strptime(sell_date_str, '%Y%m%d')
            
            today = datetime.now()
            start_date = today - timedelta(days=self.config.CHART_PERIOD_DAYS)
            end_date = today
            
            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')
            
            logger.info(f"차트 기간: {start_date_str} ~ {end_date_str}")
            logger.info(f"매매 기간: {buy_date_str} ~ {sell_date_str}")
            
            # 3. 주식 데이터 조회
            df = self.data_manager.get_stock_data(ticker, start_date_str, end_date_str)
            if df is None:
                return False
            
            # 4. 기술적 지표 계산
            ema_short, ema_long = self.indicator.calculate_ema(
                df['Close'], self.config.EMA_PERIODS
            )
            
            buy_markers, sell_markers = self.indicator.create_trade_markers(
                df, buy_date, buy_price, sell_date, sell_price
            )
            
            # 5. 추가 플롯 설정
            add_plots = [
                mpf.make_addplot(buy_markers, type='scatter', 
                               marker=self.config.BUY_MARKER, 
                               color=self.config.BUY_COLOR, 
                               markersize=self.config.MARKER_SIZE, 
                               label='Buy'),
                mpf.make_addplot(sell_markers, type='scatter', 
                               marker=self.config.SELL_MARKER, 
                               color=self.config.SELL_COLOR, 
                               markersize=self.config.MARKER_SIZE, 
                               label='Sell'),
                mpf.make_addplot(ema_short, color=self.config.EMA_COLORS[0], 
                               width=1.5, label=f'EMA {self.config.EMA_PERIODS[0]}'),
                mpf.make_addplot(ema_long, color=self.config.EMA_COLORS[1], 
                               width=1.5, label=f'EMA {self.config.EMA_PERIODS[1]}'),
            ]
            
            # 6. 차트 스타일 생성
            style = self.style_manager.create_custom_style()
            
            # 7. 파일명 생성
            stock_display_name = stock.get_market_ticker_name(ticker)
            filename = f"{stock_display_name}({ticker})_{buy_date_str}-{sell_date_str}_trade.png"
            
            # 8. 차트 생성 및 저장
            fig, axes = mpf.plot(
                df,
                type='candle',
                style=style,
                volume=True,
                addplot=add_plots,
                ylabel='가격 (원)',
                ylabel_lower='거래량',
                figsize=self.config.FIGURE_SIZE,
                returnfig=True
            )

            fig.suptitle(f'\n{stock_display_name} ({ticker}) Trading Log',  # 제목 텍스트
                x=0.55,  # 가로 위치: 중앙
                fontsize=25,              # <-- 폰트 크기 지정
                fontweight='bold',        # <-- 폰트 굵기 지정 (bold, normal 등)
                color='black'             # <-- 폰트 색상 지정
            )
            
            # 9. 제목 폰트 크기 수동 조정
            # 제목 텍스트 객체 찾기 및 폰트 크기 조정
            # for ax in fig.axes:
            #     if ax.get_title():
            #         ax.set_title(ax.get_title(), fontsize=1000, fontweight='bold', pad=20)
            
            # 10. 차트 레이아웃 조정
            fig.set_facecolor(self.config.BACKGROUND_COLOR)
            # fig.subplots_adjust(top=0.85)  # 제목 공간 확보
            
            # 11. 파일 저장
            fig.savefig(filename, bbox_inches='tight', dpi=self.config.DPI)
            plt.close(fig)  # 메모리 해제
            
            logger.info(f"차트 저장 완료: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"차트 생성 중 오류: {e}")
            return False

def main():
    """메인 함수"""
    try:
        # 설정 로드
        config = ChartConfig()
        
        # 차트 생성기 초기화
        chart_generator = ChartGenerator(config)
        
        # 입력 데이터 (실제 사용 시에는 사용자 입력으로 변경)
        input_data = {
            'stock_name': "삼성전자",
            'buy_date': "20250219",
            'buy_price': 58000,
            'sell_date': "20250625",
            'sell_price': 61000
        }
        
        logger.info("차트 생성을 시작합니다...")
        
        # 차트 생성
        success = chart_generator.generate_trade_chart(
            stock_name=input_data['stock_name'],
            buy_date_str=input_data['buy_date'],
            buy_price=input_data['buy_price'],
            sell_date_str=input_data['sell_date'],
            sell_price=input_data['sell_price']
        )
        
        if success:
            logger.info("✅ 차트 생성이 성공적으로 완료되었습니다.")
        else:
            logger.error("❌ 차트 생성에 실패했습니다.")
            
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류: {e}")

if __name__ == "__main__":
    main()