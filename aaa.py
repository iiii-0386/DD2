import datetime
import csv
import os
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, redirect

# --- 1. グローバル変数とアプリの初期化 ---
RATING_FILE = "daily_ratings.csv"  # 評価データを保存するファイル名

# テンプレートフォルダを明示的に指定 
app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)


# --- 2. データの読み書き (CSV関連) ---
def hyouka_map_wo_yomikomu():
    """CSVファイルから評価データを読み込み、辞書として返す"""
    hyouka_map = {}
    
    if not os.path.exists(RATING_FILE):
        return hyouka_map
    
    try:
        with open(RATING_FILE, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader, None)  # ヘッダー行をスキップ
            
            for row in reader:
                if len(row) == 2:
                    hyouka_map[row[0]] = int(row[1]) 
    except Exception as e:
        print(f"❌ 評価データの読み込み中にエラーが発生しました: {e}")
        return {}

    return hyouka_map


def hyouka_map_wo_hozon_suru(hyouka_map):
    """評価データをCSVファイルに書き込む"""
    try:
        with open(RATING_FILE, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['日付', '評価点'])
            
            for date_str, rating in sorted(hyouka_map.items()):
                writer.writerow([date_str, rating])
        return True
    except Exception as e:
        print(f"❌ CSVファイルへの保存中にエラーが発生しました: {e}")
        return False


# --- 3. 平均点の計算 ---
def heikinchi_wo_keisan_suru(hyouka_map):
    if not hyouka_map:
        return {'total_average': 0, 'weekly_averages': {}}

    all_ratings = list(hyouka_map.values())
    total_average = sum(all_ratings) / len(all_ratings) if all_ratings else 0

    weekly_averages = {}
    
    try:
        sorted_dates = sorted(hyouka_map.keys())
        first_date_obj = datetime.datetime.strptime(sorted_dates[0], "%Y-%m-%d").date()
        
        shuu_goto_no_group = defaultdict(list)
        for date_str, rating in hyouka_map.items():
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            saisho_kara_no_keika_nissu = (date_obj - first_date_obj).days
            shuu_bangou = saisho_kara_no_keika_nissu // 7
            shuu_goto_no_group[shuu_bangou].append(rating)

        for shuu_bangou, ratings in shuu_goto_no_group.items():
            shuu_no_kaishibi_obj = first_date_obj + datetime.timedelta(days=shuu_bangou * 7)
            shuu_no_key = shuu_no_kaishibi_obj.strftime("%Y-%m-%d")
            weekly_averages[shuu_no_key] = sum(ratings) / len(ratings)
            
    except Exception as e:
        print(f"エラー: 週間平均の計算中に問題が発生しました: {e}") 

    return {
        'total_average': total_average,
        'weekly_averages': weekly_averages
    }


# --- 4. カレンダーデータ生成 ---
def calendar_data_wo_seisei_suru(year, month, hyouka_map):
    start_of_month = datetime.date(year, month, 1)

    start_day_of_week = start_of_month.weekday()
    start_day_of_week = (start_day_of_week % 7)

    calendar_start_date = start_of_month - datetime.timedelta(days=start_day_of_week)
    calendar_weeks = []
    current_date = calendar_start_date
    
    for _ in range(6):
        week = []
        for _ in range(7):
            date_str = current_date.strftime("%Y-%m-%d")
            rating = hyouka_map.get(date_str)
            
            week.append({
                'date': date_str,
                'day': current_date.day,
                'rating': rating,
                'is_current_month': current_date.month == month 
            })
            current_date += datetime.timedelta(days=1)
        calendar_weeks.append(week)
        
    prev_month = start_of_month - datetime.timedelta(days=1)

    tsugi_no_tsuki_no_hajimari = (start_of_month + datetime.timedelta(days=32)).replace(day=1)

    return {
        'month_name': f"{year}年{month:02}月",
        'weeks': calendar_weeks,
        'prev_year': prev_month.year,
        'prev_month': prev_month.month,
        'next_year': tsugi_no_tsuki_no_hajimari.year,
        'next_month': tsugi_no_tsuki_no_hajimari.month
    }


# --- 5. ルーティング ---
@app.route('/')
def home_he_henkou_suru():
    today = datetime.date.today()
    return redirect(f"/{today.year}/{today.month}")


@app.route('/<int:year>/<int:month>')
def calendar_wo_hyouji_suru(year, month):
    hyouka_map = hyouka_map_wo_yomikomu()
    heikin_tachi = heikinchi_wo_keisan_suru(hyouka_map)
    calendar_data = calendar_data_wo_seisei_suru(year, month, hyouka_map)

    return render_template(
        'dsds.html',
        calendar=calendar_data,
        total_average=heikin_tachi['total_average'],
        weekly_averages=heikin_tachi['weekly_averages']
    )


@app.route('/update', methods=['POST'])
def hyouka_wo_koushin_suru():
    data = request.json
    date_str = data.get('date')
    rating_val = data.get('rating')

    if not date_str or rating_val is None:
        return jsonify({'success': False, 'error': '無効なデータが送信されました'}), 400

    try:
        rating_int = int(rating_val)
        if not (0 <= rating_int <= 5):
            raise ValueError("評価点の範囲が不正です (0～5)。")
        
        hyouka_map = hyouka_map_wo_yomikomu()

        if rating_int == 0:
            hyouka_map.pop(date_str, None)
        else:
            hyouka_map[date_str] = rating_int
        
        if hyouka_map_wo_hozon_suru(hyouka_map):
            heikin_tachi = heikinchi_wo_keisan_suru(hyouka_map)
            return jsonify({
                'success': True,
                'total_avg': heikin_tachi['total_average']
            })
        else:
            return jsonify({'success': False, 'error': 'ファイルの保存に失敗しました'}), 500
            
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': f'サーバーでエラー: {e}'}), 500


# --- 6. 実行 ---
if __name__ == '__main__':
    app.run(debug=True)