import requests
import json
import pandas as pd
import streamlit as st
from pubmed_api import fetch_pubmed_studies, get_pubmed_article_details, update_papers_csv

def test_pubmed_connection():
    """
    PubMed APIへの基本的な接続テストを実行します。
    """
    try:
        # 基本的なAPIエンドポイントへの接続テスト
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi?retmode=json"
        response = requests.get(url)
        response.raise_for_status()
        
        # レスポンスが有効なJSONかチェック
        result = response.json()
        
        if 'einforesult' in result:
            return {
                "status": "success",
                "message": "PubMed API基本接続テスト成功",
                "details": f"ステータスコード: {response.status_code}, API Version: {result.get('einforesult', {}).get('version', '不明')}"
            }
        else:
            return {
                "status": "warning",
                "message": "PubMed APIは応答していますが、予期しない形式です",
                "details": f"ステータスコード: {response.status_code}, レスポンス: {response.text[:200]}..."
            }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": "PubMed APIへの接続に失敗しました",
            "details": str(e)
        }
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "APIレスポンスが有効なJSONではありません",
            "details": f"ステータスコード: {response.status_code}, レスポンス: {response.text[:200]}..."
        }

def perform_test_search(keyword="orthodontic AND malocclusion", max_results=2):
    """
    テスト検索を実行し、結果を返します。
    
    Parameters:
    -----------
    keyword : str
        検索キーワード
    max_results : int
        取得する最大結果数
        
    Returns:
    --------
    dict
        テスト結果を含む辞書
    """
    try:
        # 検索実行
        search_results = fetch_pubmed_studies(keyword, max_results, 30)
        
        if not search_results or 'esearchresult' not in search_results:
            return {
                "status": "error",
                "message": "検索結果が空または無効な形式です",
                "details": str(search_results)
            }
        
        pmid_list = search_results.get('esearchresult', {}).get('idlist', [])
        
        if not pmid_list:
            return {
                "status": "warning",
                "message": "検索結果が0件でした",
                "details": f"キーワード '{keyword}' での検索結果はありませんでした"
            }
        
        # 取得したPMIDの詳細情報を取得
        articles = get_pubmed_article_details(pmid_list)
        
        if not articles:
            return {
                "status": "warning",
                "message": "論文詳細の取得に失敗しました",
                "details": f"PMID: {', '.join(pmid_list)}"
            }
        
        # 成功
        return {
            "status": "success",
            "message": f"{len(articles)}件の論文を正常に取得しました",
            "details": articles,
            "pmid_list": pmid_list
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "テスト検索実行中にエラーが発生しました",
            "details": str(e)
        }

def display_debug_ui():
    """
    デバッグ情報を表示するStreamlit UI
    """
    st.title("PubMed API連携デバッグツール")
    
    st.write("このツールでPubMed API連携が適切に機能しているか確認できます")
    
    with st.expander("1. 基本接続テスト", expanded=True):
        if st.button("基本接続テスト実行"):
            with st.spinner("PubMed APIに接続中..."):
                result = test_pubmed_connection()
                
                if result["status"] == "success":
                    st.success(result["message"])
                elif result["status"] == "warning":
                    st.warning(result["message"])
                else:
                    st.error(result["message"])
                
                st.code(result["details"])
    
    with st.expander("2. テスト検索実行", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            test_keyword = st.text_input("テスト検索キーワード", "orthodontic AND malocclusion")
        with col2:
            test_max_results = st.number_input("最大結果数", min_value=1, max_value=10, value=2)
        
        if st.button("テスト検索実行"):
            with st.spinner("検索中..."):
                result = perform_test_search(test_keyword, test_max_results)
                
                if result["status"] == "success":
                    st.success(result["message"])
                    
                    # 取得した論文情報を表示
                    articles = result["details"]
                    for i, article in enumerate(articles):
                        with st.expander(f"論文 {i+1}: {article.get('title', '不明')}"):
                            st.write(f"**著者:** {article.get('authors', '不明')}")
                            st.write(f"**掲載誌:** {article.get('journal', '不明')} ({article.get('publication_year', '不明')})")
                            st.write(f"**DOI:** {article.get('doi', '不明')}")
                            st.write(f"**PMID:** {article.get('pmid', '不明')}")
                            st.write(f"**研究タイプ:** {article.get('study_type', '不明')}")
                            st.write(f"**URL:** [PubMed]({article.get('url', '#')})")
                            
                            # 抄録の表示（長い場合は折りたたみ可能に）
                            if 'abstract' in article and article['abstract']:
                                with st.expander("抄録"):
                                    st.write(article['abstract'])
                elif result["status"] == "warning":
                    st.warning(result["message"])
                    st.code(result["details"])
                else:
                    st.error(result["message"])
                    st.code(result["details"])
    
    with st.expander("3. 論文データベース確認", expanded=True):
        try:
            papers_df = pd.read_csv('papers.csv')
            st.write(f"**現在のデータベース統計**")
            st.write(f"- 総論文数: {len(papers_df)}")
            
            # 問題別の分布
            if 'issue' in papers_df.columns:
                issue_counts = papers_df['issue'].value_counts()
                st.write("**問題別の論文数:**")
                st.bar_chart(issue_counts)
            
            # エビデンスレベル分布
            if 'evidence_level' in papers_df.columns:
                evidence_counts = papers_df['evidence_level'].value_counts()
                st.write("**エビデンスレベル分布:**")
                st.bar_chart(evidence_counts)
            
            # データベースプレビュー
            with st.expander("データベース内容プレビュー"):
                st.dataframe(papers_df)
        except Exception as e:
            st.error(f"論文データベース読み込みエラー: {str(e)}")

if __name__ == "__main__":
    # 単独実行時はデバッグUIを表示
    display_debug_ui()