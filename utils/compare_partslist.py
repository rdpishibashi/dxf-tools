from collections import Counter
import io

def normalize_label(label):
    """ラベルを正規化する（空白を削除し、大文字に変換）"""
    if label is None:
        return ""
    return label.strip().upper()

def read_labels_from_content(content):
    """
    テキスト内容からラベルを読み込む
    
    Args:
        content (str or bytes): ラベルが含まれるテキスト内容
        
    Returns:
        list: 正規化されたラベルのリスト
    """
    labels = []
    
    # バイト型の場合はデコード
    if isinstance(content, bytes):
        content = content.decode('utf-8')
    
    # 行ごとに処理
    for line in io.StringIO(content):
        label = line.strip()
        if label:  # 空行を無視
            # ラベルを正規化（大文字変換・トリム）
            label = normalize_label(label)
            labels.append(label)
    
    return labels

def compare_parts_list(dxf_labels_content, circuit_symbols_content):
    """
    図面ラベルファイルと回路記号ファイルの内容を比較する
    
    Args:
        dxf_labels_content: 図面ラベルファイルの内容
        circuit_symbols_content: 回路記号ファイルの内容
        
    Returns:
        tuple: (マークダウン形式の差分結果, 処理情報)
    """
    info = {
        "dxf_total": 0,
        "dxf_unique": 0,
        "circuit_total": 0,
        "circuit_unique": 0,
        "common_count": 0,
        "missing_in_dxf": 0,
        "missing_in_circuit": 0,
        "error": None
    }
    
    try:
        # ファイル内容からラベルを読み込む
        dxf_labels = read_labels_from_content(dxf_labels_content)
        circuit_symbols = read_labels_from_content(circuit_symbols_content)
        
        # 基本情報を設定
        info["dxf_total"] = len(dxf_labels)
        info["circuit_total"] = len(circuit_symbols)
        
        # カウンターを使って各ラベルの出現回数を集計
        dxf_counter = Counter(dxf_labels)
        circuit_counter = Counter(circuit_symbols)
        
        # ユニーク数を記録
        info["dxf_unique"] = len(dxf_counter)
        info["circuit_unique"] = len(circuit_counter)
        
        # 共通するラベル数を計算
        common_labels = set(dxf_counter.keys()) & set(circuit_counter.keys())
        info["common_count"] = len(common_labels)
        
        # 図面に不足しているラベル（回路記号にはあるが図面にない）
        missing_in_dxf = circuit_counter - dxf_counter
        missing_in_dxf_expanded = list(missing_in_dxf.elements())  # 個数分展開
        info["missing_in_dxf"] = len(missing_in_dxf_expanded)
        
        # 回路記号に不足しているラベル（図面にあるが回路記号にない）
        missing_in_circuit = dxf_counter - circuit_counter
        missing_in_circuit_expanded = list(missing_in_circuit.elements())  # 個数分展開
        info["missing_in_circuit"] = len(missing_in_circuit_expanded)
        
        # マークダウン形式で出力を生成
        output = []
        output.append("# 図面ラベルと回路記号の差分比較結果\n")
        
        output.append("## 処理概要")
        output.append(f"- 図面ラベル数: {info['dxf_total']} (ユニーク: {info['dxf_unique']})")
        output.append(f"- 回路記号数: {info['circuit_total']} (ユニーク: {info['circuit_unique']})")
        output.append(f"- 共通するユニークラベル数: {info['common_count']}")
        output.append(f"- 図面に不足しているラベル総数: {info['missing_in_dxf']}")
        output.append(f"- 回路記号に不足しているラベル総数: {info['missing_in_circuit']}")
        output.append("")
        
        output.append("## 図面に不足しているラベル（回路記号リストには存在する）")
        if missing_in_dxf_expanded:
            # 個数分展開したリストをソートして出力
            for symbol in sorted(missing_in_dxf_expanded):
                output.append(f"- {symbol}")
        else:
            output.append("- なし")
        output.append("")
        
        output.append("## 回路記号リストに不足しているラベル（図面には存在する）")
        if missing_in_circuit_expanded:
            # 個数分展開したリストをソートして出力
            for label in sorted(missing_in_circuit_expanded):
                output.append(f"- {label}")
        else:
            output.append("- なし")
        output.append("")
        
        return "\n".join(output), info
        
    except Exception as e:
        info["error"] = str(e)
        return "", info