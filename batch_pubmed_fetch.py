import time
import pandas as pd
import argparse
import sys
import os
from pathlib import Path

# 親ディレクトリへのパスを追加
sys.path.append(str(Path(__file__).parent.parent))

# pubmed_api モジュールをインポート
from pubmed_api import fetch_pubmed_studies, get_pubmed_article_details, update_papers_csv

# 歯科矯正関連の検索キーワードリスト
ORTHO_KEYWORDS = [
    # 基本的な歯列問題
    "dental crowding evidence",
    "open bite treatment orthodontic",
    "deep bite treatment orthodontic",
    "crossbite treatment evidence",
    "overjet treatment orthodontic",
    "underbite treatment evidence",
    
    # 年齢関連
    "orthodontic treatment timing children",
    "orthodontic treatment timing adolescent",
    "orthodontic treatment timing adult",
    "orthodontic treatment elderly",
    
    # リスクと効果
    "malocclusion risk untreated",
    "orthodontic treatment long term effect",
    "dental crowding oral health risk",
    "malocclusion periodontal risk",
    "malocclusion caries risk",
    "orthodontic treatment cost effectiveness",
    
    # 高エビデンスレベル研究
    "orthodontic systematic review",
    "orthodontic meta-analysis",
    "malocclusion randomized controlled trial",
    "orthodontic treatment cohort study",
    
    # 日本関連 (英語論文)
    "japanese orthodontic treatment",
    "asian orthodontic treatment",
    "japanese malocclusion prevalence"
]

def batch_fetch_articles(keywords=None, max_per_keyword=30, days_recent=365, pause_seconds=3):
    """
    一連のキーワードから論文をバッチで取得し、CSVに保存します
    
    Parameters:
    -----------
    keywords : list of str
        検索キーワードのリスト（指定がなければデフォルトリストを使用）
    max_per_keyword : int
        キーワードごとに取得する最大論文数
    days_recent : int
        何日前までの論文を検索するか
    pause_seconds : int
        APIリクエスト間の待機秒数（レート制限対策）
    
    Returns:
    --------
    int
        取得・保存された総論文数
    """
    if keywords is None:
        keywords = ORTHO_KEYWORDS
    
    total_articles = 0
    total_new_articles = 0
    
    # APIキーの存在を確認
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        print(f"NCBIのAPIキーが見つかりました。より高いレート制限でリクエストを実行します。")
        # APIキーがある場合は待機時間を短縮可能
        actual_pause = max(1, pause_seconds // 3)  # 最低1秒
    else:
        print(f"NCBIのAPIキーが見つかりません。標準のレート制限でリクエストを実行します。")
        print(f"より効率的な取得には、APIキーを設定することをお勧めします。詳細は README.md を参照してください。")
        actual_pause = pause_seconds
    
    print(f"開始: {len(keywords)}個のキーワードから論文を取得します")
    
    for i, keyword in enumerate(keywords):
        print(f"\n[{i+1}/{len(keywords)}] キーワード: '{keyword}'")
        
        try:
            # 検索実行
            print(f"  PubMed検索中...")
            search_results = fetch_pubmed_studies(keyword, max_per_keyword, days_recent)
            
            if 'esearchresult' in search_results and 'idlist' in search_results['esearchresult']:
                pmid_list = search_results['esearchresult']['idlist']
                
                if pmid_list:
                    print(f"  {len(pmid_list)}件の論文が見つかりました")
                    
                    # 論文詳細の取得
                    print(f"  論文詳細を取得中...")
                    articles = get_pubmed_article_details(pmid_list)
                    
                    # CSVに追加
                    if articles:
                        # CSVファイルの存在確認
                        csv_exists = os.path.exists('papers.csv')
                        
                        # CSVファイルを更新
                        updated_df = update_papers_csv(articles)
                        
                        # 新規追加論文数（CSVが存在した場合）
                        if csv_exists:
                            new_articles = len(articles) - (len(updated_df) - len(articles))
                            total_new_articles += new_articles
                            print(f"  {new_articles}件の新規論文をデータベースに追加しました")
                        else:
                            total_new_articles += len(articles)
                            print(f"  {len(articles)}件の論文をデータベースに追加しました")
                        
                        total_articles += len(articles)
                    else:
                        print("  論文詳細の取得に失敗しました")
                else:
                    print("  該当する論文が見つかりませんでした")
            else:
                print(f"  検索結果が無効な形式です: {search_results}")
        
        except Exception as e:
            print(f"  エラーが発生しました: {str(e)}")
        
        # 次のリクエストまで待機（レート制限対策）
        if i < len(keywords) - 1:
            print(f"  次のキーワードまで{actual_pause}秒待機中...")
            time.sleep(actual_pause)
    
    print(f"\n完了: 処理した論文数: {total_articles}, 新規追加: {total_new_articles}")
    
    # 現在のデータベース状態を表示
    try:
        db_df = pd.read_csv('papers.csv')
        print(f"\nデータベース統計:")
        print(f"- 総論文数: {len(db_df)}")
        
        if 'issue' in db_df.columns:
            issue_counts = db_df['issue'].value_counts()
            print("\n歯列問題別の論文数:")
            for issue, count in issue_counts.items():
                print(f"- {issue}: {count}件")
        
        if 'evidence_level' in db_df.columns:
            evidence_counts = db_df['evidence_level'].value_counts()
            print("\nエビデンスレベル別の論文数:")
            for level, count in evidence_counts.items():
                print(f"- レベル{level}: {count}件")
    except Exception as e:
        print(f"データベース統計の取得中にエラーが発生しました: {str(e)}")
    
    return total_new_articles

if __name__ == "__main__":
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='PubMedから歯科矯正関連の論文を一括取得します')
    parser.add_argument('--max', type=int, default=30, help='キーワードごとの最大取得数')
    parser.add_argument('--days', type=int, default=365, help='何日前までの論文を検索するか')
    parser.add_argument('--pause', type=int, default=3, help='APIリクエスト間の待機秒数')
    parser.add_argument('--custom', type=str, help='カスタムキーワード（カンマ区切り）')
    parser.add_argument('--key', type=str, help='NCBIのAPIキー（環境変数未設定の場合）')
    
    args = parser.parse_args()
    
    # コマンドラインからAPIキーが提供された場合
    if args.key:
        os.environ["NCBI_API_KEY"] = args.key
        print(f"コマンドラインからのAPIキーを使用します")
    
    # カスタムキーワードが指定された場合
    keywords = None
    if args.custom:
        keywords = [k.strip() for k in args.custom.split(',')]
        print(f"カスタムキーワード {len(keywords)}個を使用します")
    
    # 実行
    batch_fetch_articles(
        keywords=keywords,
        max_per_keyword=args.max,
        days_recent=args.days,
        pause_seconds=args.pause
    )