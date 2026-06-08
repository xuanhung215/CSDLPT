import streamlit as st
import xml.etree.ElementTree as ET
import time
import random
import re
import os
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# CẤU HÌNH MÔ PHỎNG MẠNG (NETWORK CONFIG)
# ==========================================
class NetworkSimulator:
    def __init__(self, base_latency=0.05, per_node_cost=0.000005):
        self.base_latency = base_latency
        self.per_node_cost = per_node_cost
        self.total_simulated_time = 0.0  # Tổng thời gian mạng đã sử dụng
    
    def simulate_transfer(self, num_nodes, num_connections=1):
        # Tính thời gian độ trễ (latency)
        latency = num_connections * self.base_latency
        # Tính thời gian truyền dữ liệu thực tế
        transfer_time = num_nodes * self.per_node_cost
        # Tổng thời gian = latency + transfer time
        total = latency + transfer_time
        # Cộng vào tổng thời gian mạng đã sử dụng
        self.total_simulated_time += total
        return total
    
    def reset(self):
        self.total_simulated_time = 0.0


# ==========================================
# 1. XỬ LÝ DỮ LIỆU XML VÀ PHÂN MẢNH
# ==========================================

def generate_xml_fragments(num_books_total=30000, num_fragments=3):
    # Lấy đường dẫn thư mục hiện tại (chứa file app.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Lấy đường dẫn thư mục gốc của dự án (thư mục cha của src)
    project_root = os.path.dirname(current_dir)
    # Đường dẫn đầy đủ đến file Books.xml
    large_xml_path = os.path.join(project_root, "Books.xml")
    
    # Đọc file XML gốc vào bộ nhớ
    tree = ET.parse(large_xml_path)
    root = tree.getroot()
    all_books = root.findall("book")
    
    all_books = all_books[:num_books_total]
    
    fragments = []
    books_per_fragment = num_books_total // num_fragments
    
    # Chia dữ liệu thành num_fragments phân mảnh
    for frag_idx in range(num_fragments):
        # Tạo phần tử gốc <library> cho phân mảnh hiện tại
        frag_root = ET.Element("library")
        # Tính chỉ số bắt đầu và kết thúc của phân mảnh
        start_idx = frag_idx * books_per_fragment
        end_idx = start_idx + books_per_fragment
        
        # Thêm các phần tử <book> vào phân mảnh
        for idx in range(start_idx, end_idx):
            frag_root.append(all_books[idx])
        
        fragments.append(frag_root)
    
    return fragments


def load_or_generate_fragments():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Thư mục chứa các file fragment XML
    xml_dir = os.path.join(current_dir, "xml_data")
    fragments = []
    
    # Kiểm tra xem thư mục xml_data có tồn tại không
    if os.path.exists(xml_dir):
        try:
            # Thử tải 3 file fragment từ đĩa
            for i in range(1, 4):
                file_path = os.path.join(xml_dir, f"fragment_{i}.xml")
                if os.path.exists(file_path):
                    tree = ET.parse(file_path)
                    fragments.append(tree.getroot())
            # Nếu đủ 3 phân mảnh, trả về ngay
            if len(fragments) == 3:
                return fragments
        except Exception:
            pass
    
    # Nếu không có file fragment hoặc có lỗi, tạo mới
    fragments = generate_xml_fragments()
    # Lưu các phân mảnh mới tạo vào đĩa
    save_fragments_to_disk(fragments)
    return fragments


def save_fragments_to_disk(fragments, output_dir="xml_data"):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(current_dir, output_dir)
    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    # Lưu từng phân mảnh vào file
    for i, fragment in enumerate(fragments):
        filename = os.path.join(target_dir, f"fragment_{i+1}.xml")
        tree = ET.ElementTree(fragment)
        # Định dạng XML cho dễ đọc
        if hasattr(ET, 'indent'):
            ET.indent(tree, space="  ", level=0)
        # Ghi file với encoding utf-8
        tree.write(filename, encoding="utf-8", xml_declaration=True)


# ==========================================
# 2. XPATH ENGINE
# ==========================================
def parse_xpath_query(query):
    # Khởi tạo dictionary kết quả
    result = {'raw': query, 'conditions': [], 'logic': 'and', 'result_field': None}
    
    # Regex pattern cho truy vấn có điều kiện (vd: /library/book[year>2000]/title)
    main_pattern = r'^/library/book\[(.+)\]/(\w+)$'
    match = re.match(main_pattern, query)
    
    if not match:
        # Nếu không khớp pattern có điều kiện, thử pattern không điều kiện
        no_cond_pattern = r'^/library/book/(\w+)$'
        no_cond_match = re.match(no_cond_pattern, query)
        if no_cond_match:
            result['result_field'] = no_cond_match.group(1)
            return result
        # Nếu không khớp pattern nào, báo lỗi
        raise ValueError(f"Không thể parse XPath query: {query}")
    
    # Lấy phần điều kiện và trường kết quả từ regex
    condition_str = match.group(1)
    result['result_field'] = match.group(2)
    
    # Xác định logic kết hợp các điều kiện (and/or)
    if ' and ' in condition_str:
        result['logic'] = 'and'
        parts = condition_str.split(' and ')
    elif ' or ' in condition_str:
        result['logic'] = 'or'
        parts = condition_str.split(' or ')
    else:
        # Chỉ có một điều kiện
        parts = [condition_str]
    
    # Regex pattern cho mỗi điều kiện (vd: year>2000, author='J.K. Rowling')
    cond_pattern = r"(\w+)\s*(>=|<=|!=|>|<|=)\s*['\"]?([^'\"]+?)['\"]?\s*$"
    
    # Phân tích từng điều kiện
    for part in parts:
        part = part.strip()
        cond_match = re.match(cond_pattern, part)
        if not cond_match:
            raise ValueError(f"Không thể parse điều kiện: '{part}'")
        # Thêm điều kiện vào danh sách
        result['conditions'].append({
            'field': cond_match.group(1),      # Trường dữ liệu (year, citations, ...)
            'operator': cond_match.group(2),   # Toán tử so sánh (>, <, =, ...)
            'value': cond_match.group(3).strip()  # Giá trị so sánh
        })
    
    return result


def evaluate_condition(book_element, condition):
    # Tìm phần tử con theo trường dữ liệu
    field_node = book_element.find(condition['field'])
    # Nếu không tìm thấy trường hoặc trường rỗng, trả về False
    if field_node is None or field_node.text is None:
        return False
    
    # Lấy giá trị thực tế và giá trị mong đợi
    actual_value = field_node.text.strip()
    expected_value = condition['value']
    op = condition['operator']
    
    # Thử so sánh dưới dạng số trước
    try:
        actual_num = float(actual_value)
        expected_num = float(expected_value)
        if op == '>':   return actual_num > expected_num
        if op == '<':   return actual_num < expected_num
        if op == '>=':  return actual_num >= expected_num
        if op == '<=':  return actual_num <= expected_num
        if op == '=':   return actual_num == expected_num
        if op == '!=':  return actual_num != expected_num
    except ValueError:
        pass
    
    # So sánh dưới dạng chuỗi
    if op == '=':   return actual_value == expected_value
    if op == '!=':  return actual_value != expected_value
    if op == '>':   return actual_value > expected_value
    if op == '<':   return actual_value < expected_value
    if op == '>=':  return actual_value >= expected_value
    if op == '<=':  return actual_value <= expected_value
    return False


def custom_xpath_evaluator(root, query):
    # Phân tích truy vấn
    parsed = parse_xpath_query(query)
    results = []
    
    # Duyệt qua từng phần tử <book>
    for book in root.findall("book"):
        # Nếu không có điều kiện, lấy tất cả
        if not parsed['conditions']:
            result_node = book.find(parsed['result_field'])
            if result_node is not None:
                results.append(result_node)
            continue
        
        # Đánh giá tất cả các điều kiện
        condition_results = [evaluate_condition(book, cond) for cond in parsed['conditions']]
        
        # Kiểm tra logic kết hợp (and/or)
        if parsed['logic'] == 'and':
            passed = all(condition_results)  # Tất cả điều kiện phải đúng
        else:
            passed = any(condition_results)  # Ít nhất một điều kiện đúng
        
        # Nếu thỏa mãn, thêm kết quả vào danh sách
        if passed:
            result_node = book.find(parsed['result_field'])
            if result_node is not None:
                results.append(result_node)
    
    return results


def count_nodes_in_tree(element):
    count = 1  # Đếm node hiện tại
    # Đệ quy đếm các node con
    for child in element:
        count += count_nodes_in_tree(child)
    return count


# ==========================================
# 3. ĐỊNH NGHĨA CÁC CHIẾN LƯỢC XỬ LÝ TRUY VẤN
# ==========================================
def fetch_and_filter(fragments, query, network, server_status):
    """
    Chiến lược 1: Fetch-and-Filter (Lấy toàn bộ về coordinator rồi mới lọc)
    fragments: Danh sách các phân mảnh XML
    query: Truy vấn XPath
    network: Đối tượng NetworkSimulator
    server_status: Danh sách trạng thái server (True=hoạt động, False=bị sập)
    return: (kết quả, số node truyền, thời gian thực, thời gian mạng)
    """
    network.reset()  # Đặt lại thời gian mạng
    start_time = time.time()  # Ghi nhận thời gian bắt đầu
    nodes_transferred = 0  # Tổng số node đã truyền qua mạng
    all_books = []  # Danh sách tất cả sách từ các server hoạt động
    
    # Duyệt qua từng phân mảnh (từng server)
    for i, fragment in enumerate(fragments):
        # Kiểm tra xem server có bị sập không
        if not server_status[i]:
            # Giả lập kết nối thất bại 
            network.simulate_transfer(num_nodes=0, num_connections=1)
            continue  # Bỏ qua server này
        
        # Đếm số node trong phân mảnh
        fragment_nodes = count_nodes_in_tree(fragment)
        nodes_transferred += fragment_nodes
        # Mô phỏng truyền toàn bộ phân mảnh về coordinator
        network.simulate_transfer(fragment_nodes, num_connections=1)
        # Thêm tất cả sách vào danh sách tổng
        for book in fragment.findall("book"):
            all_books.append(book)

    # Tạo cây XML tổng hợp tại coordinator
    coordinator_root = ET.Element("library")
    for book in all_books:
        coordinator_root.append(book)
    
    # Thực hiện lọc truy vấn trên cây tổng hợp
    results = custom_xpath_evaluator(coordinator_root, query)
    end_time = time.time()  # Ghi nhận thời gian kết thúc
    
    return results, nodes_transferred, (end_time - start_time), network.total_simulated_time


def fragment_first(fragments, query, network, server_status):
    """
    Chiến lược 2: Fragment-First (Lọc tại server cục bộ trước, chỉ gửi kết quả về)
    fragments: Danh sách các phân mảnh XML
    query: Truy vấn XPath
    network: Đối tượng NetworkSimulator
    server_status: Danh sách trạng thái server
    return: (kết quả, số node truyền, thời gian thực, thời gian mạng)
    """
    network.reset()  # Đặt lại thời gian mạng
    start_time = time.time()  # Ghi nhận thời gian bắt đầu
    nodes_transferred = 0  # Tổng số node đã truyền qua mạng
    results = []  # Danh sách kết quả tổng hợp
    
    # Duyệt qua từng phân mảnh (từng server)
    for i, fragment in enumerate(fragments):
        # Kiểm tra xem server có bị sập không
        if not server_status[i]:
            # Giả lập gửi request nhưng server không phản hồi
            network.simulate_transfer(num_nodes=0, num_connections=1)
            continue  # Bỏ qua server này
        
        # Thực hiện lọc truy vấn TẠI SERVER CỤC BỘ
        local_results = custom_xpath_evaluator(fragment, query)
        local_count = len(local_results)
        nodes_transferred += local_count
        # Mô phỏng truyền CHỈ KẾT QUẢ về coordinator
        network.simulate_transfer(local_count, num_connections=1)
        # Cộng kết quả cục bộ vào tổng
        results.extend(local_results)
    
    end_time = time.time()  # Ghi nhận thời gian kết thúc
    return results, nodes_transferred, (end_time - start_time), network.total_simulated_time


# ==========================================
# MAIN STREAMLIT APP
# ==========================================
def main():
    # Cấu hình trang web
    st.set_page_config(
        page_title="Distributed XPath Evaluator",
        page_icon="",
        layout="wide"  # Hiển thị theo kiểu rộng
    )
    
    st.title("Distributed XPath Evaluator - Digital Library")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("Cấu hình")
        # num_books = st.slider("Số lượng sách (tổng)", 1000, 3000, 3000)
        base_latency = st.slider("Latency (ms/connection)", 10, 200, 50) / 1000
        per_node_cost = st.slider("Cost per node (μs)", 1, 20, 5) / 1000000

        st.markdown("---")
        st.header("Giả lập trạng thái Server")
        st.markdown("Tích chọn để giả lập tình huống Server cục bộ bị sập (Offline):")
        
        # Checkbox để giả lập trạng thái server
        server_1_pool = st.checkbox("Server 1 (Fragment 1)", value=True, help="Bỏ tích để làm sập Server 1")
        server_2_pool = st.checkbox("Server 2 (Fragment 2)", value=True, help="Bỏ tích để làm sập Server 2")
        server_3_pool = st.checkbox("Server 3 (Fragment 3)", value=True, help="Bỏ tích để làm sập Server 3")
        
        server_status = [server_1_pool, server_2_pool, server_3_pool]
        
        st.markdown("---")
        st.header("Gợi ý truy vấn")
        suggested_queries = [
            "/library/book[year>2000]/title",
            "/library/book[citations>200]/author",
            "/library/book[chapters<10]/title",
            "/library/book[year>=2002 and citations>=100]/title",
            "/library/book[year>=2004 or citations>=400]/author",
            "/library/book[author='J. K. Rowling']/title",
            "/library/book/title"
        ]
        selected_query = st.selectbox("Chọn truy vấn mẫu", suggested_queries)
        
        st.markdown("---")
        st.header("Hướng dẫn")
        st.markdown("""
        **Trường dữ liệu:** title, author, year, chapters, citations  
        **Toán tử:** >, <, >=, <=, =, !=  
        **Kết hợp:** and, or  
        **Ví dụ:** `/library/book[year>2000]/title`
        """)
    
    # ==========================================
    # NỘI DUNG CHÍNH
    # ==========================================
    # Load dữ liệu (chỉ chạy lần đầu)
    if 'fragments' not in st.session_state:
        with st.spinner("Đang tải hoặc tạo dữ liệu..."):
            st.session_state.fragments = load_or_generate_fragments()
            # st.success(f"Đã tải {len(st.session_state.fragments)} fragments!")
    
    # Khởi tạo đối tượng mô phỏng mạng với tham số từ sidebar
    network = NetworkSimulator(base_latency=base_latency, per_node_cost=per_node_cost)
    
    # Tạo layout 2 cột cho ô nhập truy vấn và nút chạy
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "Nhập truy vấn XPath",
            value=selected_query,
            placeholder="/library/book[year>2020]/title"
        )
    
    with col2:
        run_button = st.button("▶Chạy đánh giá", type="primary", use_container_width=True)
    
    if run_button and query:
        try:
            
            parsed = parse_xpath_query(query)
            
            # Chạy cả 2 chiến lược
            with st.spinner("Đang chạy đánh giá..."):
                ff_results, ff_nodes, ff_time, ff_net_time = fetch_and_filter(
                    st.session_state.fragments, query, network, server_status
                )
                frag_results, frag_nodes, frag_time, frag_net_time = fragment_first(
                    st.session_state.fragments, query, network, server_status
                )
            
            st.markdown("---")
            # Hiển thị cảnh báo nếu có server bị sập
            if False in server_status:
                st.warning(f"Hệ thống đang chạy trong điều kiện có Server bị sập! Kết quả hiển thị dựa trên các Node còn hoạt động.")

            # ==========================================
            # HIỂN THỊ KẾT QUẢ SO SÁNH
            # ==========================================
            st.subheader("Kết quả so sánh")
            
            # Metrics
            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            
            with metric_col1:
                st.metric("Kết quả", f"{len(frag_results):,}")
            
            with metric_col2:
                if ff_nodes > 0:
                    # Tính phần trăm tiết kiệm mạng
                    savings = (1 - frag_nodes / ff_nodes) * 100
                    st.metric("Tiết kiệm mạng", f"{savings:.1f}%", delta=f"-{100-savings:.1f}%")
            
            with metric_col3:
                if frag_time > 0:
                    # Tính tốc độ nhanh hơn bao nhiêu lần
                    speedup = ff_time / frag_time
                    st.metric("Tốc độ", f"{speedup:.1f}x", delta=f"{speedup:.1f}x")
            
            with metric_col4:
                st.metric("Nodes truyền", f"{frag_nodes:,}", delta=f"-{ff_nodes - frag_nodes:,}")
            
            # Hiển thị biểu đồ so sánh
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                fig_nodes = go.Figure(data=[
                    go.Bar(name='Fetch-and-Filter', x=['Nodes'], y=[ff_nodes], marker_color='#ff6b6b'),
                    go.Bar(name='Fragment-First', x=['Nodes'], y=[frag_nodes], marker_color='#51cf66')
                ])
                fig_nodes.update_layout(title="Số node truyền qua mạng", barmode='group')
                st.plotly_chart(fig_nodes, use_container_width=True)
            
            with chart_col2:
                fig_time = go.Figure(data=[
                    go.Bar(name='Fetch-and-Filter', x=['Thời gian (ms)'], y=[ff_time*1000], marker_color='#ff6b6b'),
                    go.Bar(name='Fragment-First', x=['Thời gian (ms)'], y=[frag_time*1000], marker_color='#51cf66')
                ])
                fig_time.update_layout(title="Thời gian thực thi", barmode='group')
                st.plotly_chart(fig_time, use_container_width=True)
            
            # Hiển thị bảng chi tiết
            st.subheader("Chi tiết")
            details_df = pd.DataFrame({
                'Thuộc tính': ['Kết quả', 'Nodes truyền', 'Thời gian thực (ms)', 'Thời gian mạng (ms)'],
                'Fetch-and-Filter': [len(ff_results), f"{ff_nodes:,}", f"{ff_time*1000:.1f}", f"{ff_net_time*1000:.1f}"],
                'Fragment-First': [len(frag_results), f"{frag_nodes:,}", f"{frag_time*1000:.1f}", f"{frag_net_time*1000:.1f}"]
            })
            st.table(details_df)
            
            # Hiển thị kết quả mẫu
            st.subheader("Kết quả mẫu")
            if frag_results:
                sample = frag_results[:10]
                sample_df = pd.DataFrame({
                    'STT': range(1, len(sample)+1),
                    'Giá trị': [node.text for node in sample]
                })
                st.dataframe(sample_df, use_container_width=True, hide_index=True)
                if len(frag_results) > 10:
                    st.info(f"... và {len(frag_results) - 10} kết quả khác")
            else:
                st.info("Không có kết quả nào")
            
        except Exception as e:
            st.error(f"Lỗi: {e}")
            st.info("Vui lòng kiểm tra lại cú pháp truy vấn XPath!")


if __name__ == "__main__":
    main()

