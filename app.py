import streamlit as st
import pandas as pd
import io
import tempfile
import os
import sys
import traceback

# モジュールのインポート
from utils.extract_labels import extract_labels
from utils.structure_record import analyze_dxf_structure 
from utils.hierarchy import extract_hierarchy
from utils.compare_dxf import compare_dxf_files_and_generate_dxf
from utils.compare_text import compare_labels

def save_uploadedfile(uploadedfile):
    """アップロードされたファイルを一時ディレクトリに保存する"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as f:
        f.write(uploadedfile.getbuffer())
        return f.name

def create_download_link(data, filename, text="Download file"):
    """ダウンロード用のリンクを生成する"""
    from base64 import b64encode
    b64 = b64encode(data).decode()
    href = f'<a href="data:file/octet-stream;base64,{b64}" download="{filename}">{text}</a>'
    return href

def main():
    st.set_page_config(
        page_title="DXF file Anlysis Tools",
        page_icon="📊",
        layout="wide",
    )
    
    st.title('DXF file Analysis Tools')
    st.write('CADで出力されたDXFファイルを分析・比較するツールです')
    
    tool_selection = st.sidebar.radio(
        'ツールを選択',
        [
            'ラベル抽出（テキスト出力）', 
            '構造分析（Excel出力）', 
            '構造分析（テキスト出力）', 
            '図形差分抽出（DXF出力）', 
            'ラベル差分抽出（テキスト出力）'
        ]
    )

    if tool_selection == 'ラベル抽出（テキスト出力）':
        st.header('DXFファイルからラベルを抽出')
        uploaded_file = st.file_uploader("DXFファイルをアップロード", type="dxf", key="label_extractor")
        
        output_filename = st.text_input("出力ファイル名", "labels.txt")
        if not output_filename.endswith('.txt'):
            output_filename += '.txt'
        
        # 新しいオプション
        col1, col2 = st.columns(2)
        with col1:
            filter_option = st.checkbox(
                "部品番号フィルター", 
                value=False, 
                help="以下の条件に合致するラベルは部品番号でないと判断して除外します："
                     "\n- 最初の文字が「(」のラベル"
                     "\n- 最初の文字が数字のラベル"
                     "\n- 最初の文字が英小文字のラベル"
                     "\n- 「GND」を含むラベル"
                     "\n- 英字１文字のみのラベル（例：R, C）"
                     "\n- 英字１文字に続いて数字（例：R1, C2, L3）"
                     "\n- 英字１文字に続いて数字と「.」からなる文字列の組み合わせ（例：C1.1, R5.2, L1.1, N1.3）"
                     "\n- 英字と「+」もしくは「-」の組み合わせ（例：A+, VCC-）"
            )
        
        with col2:
            sort_option = st.selectbox(
                "ソート順", 
                options=[
                    ("ソートなし", "none"), 
                    ("昇順", "asc"), 
                    ("降順", "desc")
                ],
                format_func=lambda x: x[0],
                help="ラベルのソート順を指定します"
            )
            sort_value = sort_option[1]  # タプルの2番目の要素（実際の値）を取得
            
        debug_option = st.checkbox("デバッグ情報を表示", value=False, help="フィルタリングの詳細情報を表示します")
            
        if uploaded_file is not None:
            try:
                # ファイルを一時ディレクトリに保存
                temp_file = save_uploadedfile(uploaded_file)
                
                if st.button("ラベルを抽出"):
                    with st.spinner('ラベルを抽出中...'):
                        labels, info = extract_labels(
                            temp_file, 
                            filter_non_parts=filter_option, 
                            sort_order=sort_value, 
                            debug=debug_option
                        )
                        
                        # 結果を表示
                        st.subheader("抽出されたラベル")
                        
                        # 処理情報の表示
                        st.info(f"元の抽出ラベル総数: {info['total_extracted']}")
                        
                        if filter_option:
                            st.info(f"フィルタリングで除外したラベル数: {info['filtered_count']}")
                        
                        st.info(f"最終的なラベル数: {info['final_count']}")
                        
                        if sort_value != "none":
                            sort_text = "昇順" if sort_value == "asc" else "降順"
                            st.info(f"ラベルを{sort_text}でソートしました")
                        
                        # ラベル一覧
                        st.text_area("ラベル一覧", "\n".join(labels), height=300)
                        
                        # ダウンロードボタンを作成
                        if labels:
                            txt_str = "\n".join(labels)
                            st.download_button(
                                label="テキストファイルをダウンロード",
                                data=txt_str.encode('utf-8'),
                                file_name=output_filename,
                                mime="text/plain",
                            )
                    
                    # 一時ファイルの削除
                    os.unlink(temp_file)
            
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.error(traceback.format_exc())

    elif tool_selection == '構造分析（Excel出力）':
        st.header('DXFデータ構造を分析してExcelファイルに出力')
        uploaded_file = st.file_uploader("DXFファイルをアップロード", type="dxf", key="structure_analyzer")
        
        output_filename = st.text_input("出力ファイル名", "structure.xlsx")
        if not output_filename.endswith('.xlsx'):
            output_filename += '.xlsx'
            
        if uploaded_file is not None:
            try:
                # ファイルを一時ディレクトリに保存
                temp_file = save_uploadedfile(uploaded_file)
                
                if st.button("構造を分析"):
                    with st.spinner('DXF構造を分析中...'):
                        data = analyze_dxf_structure(temp_file)
                        df = pd.DataFrame(data, columns=['Section', 'Entity', 'GroupCode', 'GroupCode Definition', 'Value'])
                        
                        # 結果をデータフレームとして表示
                        st.subheader("構造分析結果")
                        st.dataframe(df, height=400)
                        
                        # Excelファイルを作成してダウンロードボタンを表示
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False, sheet_name='DXF構造')
                        
                        excel_data = output.getvalue()
                        st.download_button(
                            label="Excelファイルをダウンロード",
                            data=excel_data,
                            file_name=output_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    
                    # 一時ファイルの削除
                    os.unlink(temp_file)
            
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.error(traceback.format_exc())

    elif tool_selection == '構造分析（テキスト出力）':
        st.header('DXFデータ構造を分析してMarkdown形式で出力')
        uploaded_file = st.file_uploader("DXFファイルをアップロード", type="dxf", key="hierarchy_extractor")
        
        output_filename = st.text_input("出力ファイル名", "hierarchy.md")
        if not output_filename.endswith('.md'):
            output_filename += '.md'
            
        if uploaded_file is not None:
            try:
                # ファイルを一時ディレクトリに保存
                temp_file = save_uploadedfile(uploaded_file)
                
                if st.button("構造を分析"):
                    with st.spinner('DXF構造を分析中...'):
                        hierarchy_lines = extract_hierarchy(temp_file)
                        
                        # 結果を表示
                        st.subheader("構造分析結果")
                        st.text_area("Markdown形式", "\n".join(hierarchy_lines), height=300)
                        
                        # ダウンロードボタンを作成
                        md_str = "\n".join(hierarchy_lines)
                        st.download_button(
                            label="Markdownファイルをダウンロード",
                            data=md_str.encode('utf-8'),
                            file_name=output_filename,
                            mime="text/markdown",
                        )
                    
                    # 一時ファイルの削除
                    os.unlink(temp_file)
            
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.error(traceback.format_exc())

    elif tool_selection == '図形差分抽出（DXF出力）':
        st.header('2つのDXFファイルの図形を比較し差分を抽出')
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_file_a = st.file_uploader("基準DXFファイル (A)", type="dxf", key="dxf_a")
        
        with col2:
            uploaded_file_b = st.file_uploader("比較対象DXFファイル (B)", type="dxf", key="dxf_b")
        
        output_filename = st.text_input("出力ファイル名", "diff.dxf")
        if not output_filename.endswith('.dxf'):
            output_filename += '.dxf'
        
        tolerance = st.slider("許容誤差", min_value=1e-8, max_value=1e-1, value=1e-6, format="%.8f")
        
        if uploaded_file_a is not None and uploaded_file_b is not None:
            try:
                # ファイルを一時ディレクトリに保存
                temp_file_a = save_uploadedfile(uploaded_file_a)
                temp_file_b = save_uploadedfile(uploaded_file_b)
                temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".dxf").name
                
                if st.button("差分を比較"):
                    with st.spinner('DXFファイルを比較中...'):
                        result = compare_dxf_files_and_generate_dxf(temp_file_a, temp_file_b, temp_output, tolerance)
                        
                        if result:
                            st.success("DXFファイルの比較が完了しました")
                            
                            # 結果ファイルを読み込んでダウンロードボタンを作成
                            with open(temp_output, 'rb') as f:
                                dxf_data = f.read()
                                
                            st.download_button(
                                label="差分DXFファイルをダウンロード",
                                data=dxf_data,
                                file_name=output_filename,
                                mime="application/dxf",
                            )
                        else:
                            st.error("DXFファイルの比較に失敗しました")
                    
                    # 一時ファイルの削除
                    os.unlink(temp_file_a)
                    os.unlink(temp_file_b)
                    os.unlink(temp_output)
            
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.error(traceback.format_exc())

    elif tool_selection == 'ラベル差分抽出（テキスト出力）':
        st.header('2つのDXFファイルのラベルを比較し差分を抽出')
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_file_a = st.file_uploader("基準DXFファイル (A)", type="dxf", key="label_a")
        
        with col2:
            uploaded_file_b = st.file_uploader("比較対象DXFファイル (B)", type="dxf", key="label_b")
        
        output_filename = st.text_input("出力ファイル名", "label_diff.md")
        if not output_filename.endswith('.md'):
            output_filename += '.md'
        
        if uploaded_file_a is not None and uploaded_file_b is not None:
            try:
                # ファイルを一時ディレクトリに保存
                temp_file_a = save_uploadedfile(uploaded_file_a)
                temp_file_b = save_uploadedfile(uploaded_file_b)
                
                if st.button("ラベル差分を比較"):
                    with st.spinner('DXFラベルを比較中...'):
                        comparison_result = compare_labels(temp_file_a, temp_file_b)
                        
                        # 結果を表示
                        st.subheader("ラベル差分抽出結果")
                        st.markdown(comparison_result)
                        
                        # ダウンロードボタンを作成
                        st.download_button(
                            label="Markdownファイルをダウンロード",
                            data=comparison_result.encode('utf-8'),
                            file_name=output_filename,
                            mime="text/markdown",
                        )
                    
                    # 一時ファイルの削除
                    os.unlink(temp_file_a)
                    os.unlink(temp_file_b)
            
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.error(traceback.format_exc())

if __name__ == '__main__':
    main()
