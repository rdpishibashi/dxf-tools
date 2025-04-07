import ezdxf
import re

# DXFフォーマットコード除去用の正規表現
FORMAT_CODE_PATTERN = re.compile(r'(\\[A-Za-z0-9\.]+;)')

def is_non_part_number(label, debug=False):
    """
    ラベルが部品番号ではないと判断される条件をチェック
    
    Args:
        label (str): チェック対象のラベル
        debug (bool): デバッグ情報を出力するかどうか
        
    Returns:
        bool: 部品番号ではないと思われる場合はTrue
    """
    if not label or len(label) == 0:
        if debug: print(f"空文字列なのでフィルタリング対象: '{label}'")
        return True
        
    # 最初の文字が「(」のラベル
    if label.startswith('('):
        if debug: print(f"'('で始まるのでフィルタリング対象: '{label}'")
        return True
        
    # 最初の文字が数字のラベル
    if label[0].isdigit():
        if debug: print(f"数字で始まるのでフィルタリング対象: '{label}'")
        return True
        
    # 最初の文字が英小文字のラベル
    if label[0].islower():
        if debug: print(f"英小文字で始まるのでフィルタリング対象: '{label}'")
        return True
        
    # 「GND」を含むラベル
    if 'GND' in label:
        if debug: print(f"'GND'を含むのでフィルタリング対象: '{label}'")
        return True
        
    # 英字1文字のみのラベル（例：R, C）
    if len(label) == 1 and label.isalpha():
        if debug: print(f"英字1文字のみなのでフィルタリング対象: '{label}'")
        return True
    
    # 英字1文字に続いて数字のパターン（例：R1, C2, L3）
    single_letter_number_pattern = r'^[A-Za-z][0-9]+$'
    if re.match(single_letter_number_pattern, label):
        if debug: print(f"英字1文字+数字パターンなのでフィルタリング対象: '{label}'")
        return True
    
    # 英字1文字に続いて数字と「.」からなる文字列の組み合わせ（例：C1.1, R5.2, L1.1, N1.3）
    single_letter_dot_pattern = r'^[A-Za-z][0-9]+\.[0-9]+$'
    if re.match(single_letter_dot_pattern, label):
        if debug: print(f"英字1文字+数字+ドット+数字パターンなのでフィルタリング対象: '{label}'")
        return True
    
    # 英字と「+」もしくは「-」の組み合わせ（例：A+, VCC-）
    alpha_plusminus_pattern = r'^[A-Za-z]+[\+\-]$'
    if re.match(alpha_plusminus_pattern, label):
        if debug: print(f"英字+[-+]パターンなのでフィルタリング対象: '{label}'")
        return True
        
    if debug: print(f"部品番号と判断: '{label}'")
    return False

def extract_labels(dxf_file, filter_non_parts=False, sort_order='none', debug=False):
    """
    DXFファイルからラベル（MTEXTエンティティ）を抽出する
    
    Args:
        dxf_file: DXFファイルパス
        filter_non_parts (bool): 部品番号以外のラベルをフィルタリングするかどうか
        sort_order (str): ソート順 ('asc'=昇順, 'desc'=降順, 'none'=ソートなし)
        debug (bool): デバッグ情報を出力するかどうか
        
    Returns:
        list: 抽出されたラベルのリスト
        dict: 処理情報（抽出数、フィルタ数など）
    """
    doc = ezdxf.readfile(dxf_file)
    msp = doc.modelspace()

    labels = []
    raw_labels = []  # フィルタリング前の全ラベル

    # モデルスペース内のMTEXTのみ抽出
    for entity in msp:
        if entity.dxftype() == 'MTEXT':
            text = entity.dxf.text
            cleaned = FORMAT_CODE_PATTERN.sub('', text)
            cleaned = cleaned.replace('\\P', ' ').strip()  # 段落コードも除去
            
            if cleaned:
                raw_labels.append(cleaned)

    # フィルタリングオプションが有効な場合
    filtered_count = 0
    if filter_non_parts:
        filtered_labels = []
        for label in raw_labels:
            if not is_non_part_number(label, debug):
                filtered_labels.append(label)
            else:
                filtered_count += 1
        
        labels = filtered_labels
    else:
        labels = raw_labels

    # ソートオプションに応じてソート
    if sort_order == 'asc':
        labels.sort()
    elif sort_order == 'desc':
        labels.sort(reverse=True)

    # 処理情報
    info = {
        'total_extracted': len(raw_labels),
        'filtered_count': filtered_count,
        'final_count': len(labels)
    }

    return labels, info
