import streamlit as st
import pandas as pd
import io
import tempfile
import os
import sys
import traceback

# モジュールのインポート
from utils.extract_labels import extract_labels
from utils.analyze_structure import analyze_dxf_structure
from utils.extract_hierachy import extract_hierachy
from utils.compare_dxf import compare_dxf_files_and_generate_dxf
from utils.compare_labels import compare_labels
from utils.extract_symbols import extract_circuit_symbols
from utils.compare_partslist import compare_parts_list, normalize_label

def save_uploadedfile(uploadedfile):
    """アップロードされたファイルを一時ディレクトリに保存する"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploadedfile.name)[1]) as f:
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
        page_title="DXF file Analysis Tools",
        page_icon="📊",
        layout="wide",
    )
    
    st.title('DXF file Analysis Tools')
    st.write('CADで出力されたDXFファイルを分析・比較するツールです')
    
    # メニュー順序を元の順序に合わせる
    tool_selection = st.sidebar.radio(
        'ツールを選択',
        [
            'ラベル抽出（テキスト出力）', 
            '構造分析（Excel出力）', 
            '構造分析（テキスト出力）', 
            '図形差分抽出（DXF出力）', 
            'ラベル差分抽出（テキスト出力）',
            '回路記号抽出（テキスト出力）',
            'パーツリスト差分抽出（テキスト出力）'
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
                "回路記号（候補）のみ抽出", 
                value=False, 
                help="以下の条件に合致するラベルは回路記号でないと判断して除外します："
                     "\n- 最初の文字が「(」（例：(BK), (M5)）"
                     "\n- 最初の文字が数字（例：2.1+, 500DJ）"
                     "\n- 英大文字だけで2文字以下（E, L, PE）"
                     "\n- 英大文字１文字に続いて数字（例：R1, T2）"
                     "\n- 英大文字１文字に続いて数字と「.」からなる文字列（例：L1.1, P01）"
                     "\n- 英字と「+」もしくは「-」の組み合わせ（例：P+, VCC-）"
                     "\n- 「GND」を含む（例：GND, GND(M4)）"
                     "\n- 「AWG」ではじまるラベル（例：AWG14, AWG18）"
                     "\n- 英小文字だけの単語と空白を複数含むラベル（例：on ..., to ...）"
                     "\n- 「☆」ではじまるラベル"
                     "\n- 「注」ではじまるラベル"
                     "\n- ラベルの文字列中の「(」ではじまり「)」で閉じる文字列部分を削除"
            )
        
        with col2:
            sort_option = st.selectbox(
                "並び替え", 
                options=[
                    ("昇順", "asc"), 
                    ("逆順", "desc"),
                    ("並び替えなし", "none")
                ],
                format_func=lambda x: x[0],
                help="ラベルの並び替え順を指定します",
                index=0  # デフォルトで昇順を選択
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
                            sort_text = "昇順" if sort_value == "asc" else "逆順"
                            st.info(f"ラベルを{sort_text}で並び替えました")
                        
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
                        hierachy_lines = extract_hierachy(temp_file)
                        
                        # 結果を表示
                        st.subheader("構造分析結果")
                        st.text_area("Markdown形式", "\n".join(hierachy_lines), height=300)
                        
                        # ダウンロードボタンを作成
                        md_str = "\n".join(hierachy_lines)
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
   
    elif tool_selection == '回路記号抽出（テキスト出力）':
        st.header('ULKES Excelファイルから回路記号を抽出')
        
        uploaded_file = st.file_uploader("Excelファイルをアップロード", type=["xlsx"], key="circuit_extractor")
        
        # アセンブリ番号入力
        col1, col2 = st.columns(2)
        with col1:
            output_filename = st.text_input("出力ファイル名", "circuit_symbols.txt")
            if not output_filename.endswith('.txt'):
                output_filename += '.txt'
        
        with col2:
            use_filename = st.checkbox("ファイル名を図面番号号として使用", value=True)
            assembly_number = None if use_filename else st.text_input("図面番号", "")
            
        if uploaded_file is not None:
            try:
                # ファイルを一時ディレクトリに保存
                temp_file = save_uploadedfile(uploaded_file)
                
                if st.button("回路記号を抽出"):
                    with st.spinner('回路記号を抽出中...'):
                        # ファイル名からアセンブリ番号を取得
                        if use_filename:
                            filename = os.path.basename(uploaded_file.name)
                            assembly_number = os.path.splitext(filename)[0]
                        
                        # 回路記号を抽出
                        symbols, info = extract_circuit_symbols(temp_file, assembly_number)
                        
                        # 処理結果の表示
                        st.subheader("抽出結果")
                        
                        if info["error"]:
                            st.error(f"エラー: {info['error']}")
                        else:
                            st.info(f"図面番号: {info['assembly_number']}")
                            st.info(f"対象データ行数: {info['processed_rows']} / {info['total_rows']}")
                            st.info(f"抽出された回路記号数: {info['total_symbols']}")
                            
                            # 抽出された回路記号の表示
                            st.text_area("回路記号リスト", "\n".join(symbols), height=300)
                            
                            # ダウンロードボタンを作成
                            if symbols:
                                txt_str = "\n".join(symbols)
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

    elif tool_selection == 'パーツリスト差分抽出（テキスト出力）':
        st.header('2つのパーツリストを比較し差分を抽出')
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_file_a = st.file_uploader("パーツリスト・ファイルA", type=["txt"], key="partslist_a")
        
        with col2:
            uploaded_file_b = st.file_uploader("パーツリスト・ファイルB", type=["txt"], key="partslist_b")
        
        output_filename = st.text_input("出力ファイル名", "partslist_diff.md")
        if not output_filename.endswith('.md'):
            output_filename += '.md'
        
        if uploaded_file_a is not None and uploaded_file_b is not None:
            try:
                # ファイルを一時ディレクトリに保存
                temp_file_a = save_uploadedfile(uploaded_file_a)
                temp_file_b = save_uploadedfile(uploaded_file_b)
                
                if st.button("パーツリスト差分を比較"):
                    with st.spinner('パーツリストを比較中...'):
                        try:
                            # パーツリストの比較
                            comparison_result = compare_parts_list(temp_file_a, temp_file_b)
                            
                            # 結果を表示
                            st.subheader("パーツリスト差分抽出結果")
                            st.markdown(comparison_result)
                            
                            # ダウンロードボタンを作成
                            st.download_button(
                                label="Markdownファイルをダウンロード",
                                data=comparison_result.encode('utf-8'),
                                file_name=output_filename,
                                mime="text/markdown",
                            )
                        except Exception as e:
                            st.error(f"比較処理中にエラーが発生しました: {str(e)}")
                            st.error(traceback.format_exc())
                    
                    # 一時ファイルの削除
                    try:
                        os.unlink(temp_file_a)
                        os.unlink(temp_file_b)
                    except:
                        pass
            
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.error(traceback.format_exc())

if __name__ == '__main__':
    main()