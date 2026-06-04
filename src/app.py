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
        self.total_simulated_time = 0.0
    
    def simulate_transfer(self, num_nodes, num_connections=1):
        latency = num_connections * self.base_latency
        transfer_time = num_nodes * self.per_node_cost
        total = latency + transfer_time
        self.total_simulated_time += total
        return total
    
    def reset(self):
        self.total_simulated_time = 0.0


# ==========================================
# 1. DỮ LIỆU MÔ PHỎNG
# ==========================================

def generate_xml_fragments(num_books_total=30000, num_fragments=3):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    csv_path = os.path.join(project_root, "Books.csv")
    
    # Read the CSV file
    df = pd.read_csv(csv_path, encoding='utf-8')
    
    # Take the first num_books_total records
    df = df.head(num_books_total)
    
    fragments = []
    books_per_fragment = num_books_total // num_fragments
    
    for frag_idx in range(num_fragments):
        root = ET.Element("library")
        start_idx = frag_idx * books_per_fragment
        end_idx = start_idx + books_per_fragment
        
        for idx in range(start_idx, end_idx):
            row = df.iloc[idx]
            book_id = idx + 1
            book = ET.SubElement(root, "book", id=str(book_id))
            
            title = ET.SubElement(book, "title")
            title.text = str(row["Book-Title"]) + " vol " + str(frag_idx + 1)
            
            author = ET.SubElement(book, "author")
            author.text = str(row["Book-Author"])
            
            year = ET.SubElement(book, "year")
            year.text = str(row["Year-Of-Publication"])
            
            chapters = ET.SubElement(book, "chapters")
            chapters.text = str(random.randint(5, 40))
            
            citations = ET.SubElement(book, "citations")
            citations.text = str(random.randint(0, 1000))
        
        fragments.append(root)
    
    return fragments


def load_or_generate_fragments():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    xml_dir = os.path.join(current_dir, "xml_data")
    fragments = []
    
    if os.path.exists(xml_dir):
        try:
            for i in range(1, 4):
                file_path = os.path.join(xml_dir, f"fragment_{i}.xml")
                if os.path.exists(file_path):
                    tree = ET.parse(file_path)
                    fragments.append(tree.getroot())
            if len(fragments) == 3:
                return fragments
        except Exception:
            pass
    
    fragments = generate_xml_fragments()
    save_fragments_to_disk(fragments)
    return fragments


def save_fragments_to_disk(fragments, output_dir="xml_data"):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(current_dir, output_dir)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    for i, fragment in enumerate(fragments):
        filename = os.path.join(target_dir, f"fragment_{i+1}.xml")
        tree = ET.ElementTree(fragment)
        if hasattr(ET, 'indent'):
            ET.indent(tree, space="  ", level=0)
        tree.write(filename, encoding="utf-8", xml_declaration=True)


# ==========================================
# 2. XPATH ENGINE
# ==========================================
def parse_xpath_query(query):
    result = {'raw': query, 'conditions': [], 'logic': 'and', 'result_field': None}
    main_pattern = r'^/library/book\[(.+)\]/(\w+)$'
    match = re.match(main_pattern, query)
    if not match:
        no_cond_pattern = r'^/library/book/(\w+)$'
        no_cond_match = re.match(no_cond_pattern, query)
        if no_cond_match:
            result['result_field'] = no_cond_match.group(1)
            return result
        raise ValueError(f"Không thể parse XPath query: {query}")
    condition_str = match.group(1)
    result['result_field'] = match.group(2)
    if ' and ' in condition_str:
        result['logic'] = 'and'
        parts = condition_str.split(' and ')
    elif ' or ' in condition_str:
        result['logic'] = 'or'
        parts = condition_str.split(' or ')
    else:
        parts = [condition_str]
    cond_pattern = r"(\w+)\s*(>=|<=|!=|>|<|=)\s*['\"]?([^'\"]+?)['\"]?\s*$"
    for part in parts:
        part = part.strip()
        cond_match = re.match(cond_pattern, part)
        if not cond_match:
            raise ValueError(f"Không thể parse điều kiện: '{part}'")
        result['conditions'].append({
            'field': cond_match.group(1),
            'operator': cond_match.group(2),
            'value': cond_match.group(3).strip()
        })
    return result


def evaluate_condition(book_element, condition):
    field_node = book_element.find(condition['field'])
    if field_node is None or field_node.text is None:
        return False
    actual_value = field_node.text.strip()
    expected_value = condition['value']
    op = condition['operator']
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
    if op == '=':   return actual_value == expected_value
    if op == '!=':  return actual_value != expected_value
    if op == '>':   return actual_value > expected_value
    if op == '<':   return actual_value < expected_value
    if op == '>=':  return actual_value >= expected_value
    if op == '<=':  return actual_value <= expected_value
    return False


def custom_xpath_evaluator(root, query):
    parsed = parse_xpath_query(query)
    results = []
    for book in root.findall("book"):
        if not parsed['conditions']:
            result_node = book.find(parsed['result_field'])
            if result_node is not None:
                results.append(result_node)
            continue
        condition_results = [evaluate_condition(book, cond) for cond in parsed['conditions']]
        if parsed['logic'] == 'and':
            passed = all(condition_results)
        else:
            passed = any(condition_results)
        if passed:
            result_node = book.find(parsed['result_field'])
            if result_node is not None:
                results.append(result_node)
    return results


def count_nodes_in_tree(element):
    count = 1
    for child in element:
        count += count_nodes_in_tree(child)
    return count


# ==========================================
# 3. CHIẾN LƯỢC
# ==========================================
def fetch_and_filter(fragments, query, network, server_status):
    network.reset()
    start_time = time.time()
    nodes_transferred = 0
    all_books = []
    for i, fragment in enumerate(fragments):
        # NẾU SERVER BỊ SẬP (Trạng thái = False)
        if not server_status[i]:
            # Giả lập độ trễ kết nối thất bại (timeout mất 1 giây)
            network.simulate_transfer(num_nodes=0, num_connections=1)
            continue # Bỏ qua không lấy được node nào từ server này

        fragment_nodes = count_nodes_in_tree(fragment)
        nodes_transferred += fragment_nodes
        network.simulate_transfer(fragment_nodes, num_connections=1)
        for book in fragment.findall("book"):
            all_books.append(book)

    coordinator_root = ET.Element("library")
    for book in all_books:
        coordinator_root.append(book)
    results = custom_xpath_evaluator(coordinator_root, query)
    end_time = time.time()
    return results, nodes_transferred, (end_time - start_time), network.total_simulated_time


def fragment_first(fragments, query, network, server_status):
    network.reset()
    start_time = time.time()
    nodes_transferred = 0
    results = []

    for i, fragment in enumerate(fragments):
        # NẾU SERVER BỊ SẬP (Trạng thái = False)
        if not server_status[i]:
            # Giả lập gửi request đi nhưng server không phản hồi
            network.simulate_transfer(num_nodes=0, num_connections=1)
            continue # Bỏ qua không nhận được kết quả lọc từ server này
        
        local_results = custom_xpath_evaluator(fragment, query)
        local_count = len(local_results)
        nodes_transferred += local_count
        network.simulate_transfer(local_count, num_connections=1)
        results.extend(local_results)
    end_time = time.time()
    return results, nodes_transferred, (end_time - start_time), network.total_simulated_time


# ==========================================
# MAIN STREAMLIT APP
# ==========================================
def main():
    st.set_page_config(
        page_title="Distributed XPath Evaluator",
        page_icon="",
        layout="wide"
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
        
        # Tạo 3 trạng thái lưu vào session_state của Streamlit
        server_1_pool = st.checkbox("Server 1 (Fragment 1)", value=True, help="Bỏ tích để làm sập Server 1")
        server_2_pool = st.checkbox("Server 2 (Fragment 2)", value=True, help="Bỏ tích để làm sập Server 2")
        server_3_pool = st.checkbox("Server 3 (Fragment 3)", value=True, help="Bỏ tích để làm sập Server 3")
        
        # Lưu trạng thái vào một danh sách để tiện vòng lặp
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
        **Ví dụ:** `/library/book[year>2020]/title`
        """)
    
    # Load data
    if 'fragments' not in st.session_state:
        with st.spinner("Đang tải hoặc tạo dữ liệu..."):
            st.session_state.fragments = load_or_generate_fragments()
            st.success(f"Đã tải {len(st.session_state.fragments)} fragments!")
    
    network = NetworkSimulator(base_latency=base_latency, per_node_cost=per_node_cost)
    
    # Main content
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
            # Parse query
            parsed = parse_xpath_query(query)
            
            # Run both strategies
            with st.spinner("Đang chạy đánh giá..."):
                ff_results, ff_nodes, ff_time, ff_net_time = fetch_and_filter(st.session_state.fragments, query, network, server_status)
                frag_results, frag_nodes, frag_time, frag_net_time = fragment_first(st.session_state.fragments, query, network, server_status)
            
            st.markdown("---")
            # Thêm vào ngay dưới st.markdown("---") khi hiển thị kết quả
            if False in server_status:
                st.warning(f"Hệ thống đang chạy trong điều kiện có Server bị sập! Kết quả hiển thị dựa trên các Node còn hoạt động.")

            # Display results
            st.subheader("Kết quả so sánh")
            
            # Metrics
            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            
            with metric_col1:
                st.metric("Kết quả", f"{len(frag_results):,}")
            
            with metric_col2:
                if ff_nodes > 0:
                    savings = (1 - frag_nodes / ff_nodes) * 100
                    st.metric("Tiết kiệm mạng", f"{savings:.1f}%", delta=f"-{100-savings:.1f}%")
            
            with metric_col3:
                if frag_time > 0:
                    speedup = ff_time / frag_time
                    st.metric("Tốc độ", f"{speedup:.1f}x", delta=f"{speedup:.1f}x")
            
            with metric_col4:
                st.metric("Nodes truyền", f"{frag_nodes:,}", delta=f"-{ff_nodes - frag_nodes:,}")
            
            # Comparison chart
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
            
            # Detailed table
            st.subheader("Chi tiết")
            details_df = pd.DataFrame({
                'Thuộc tính': ['Kết quả', 'Nodes truyền', 'Thời gian thực (ms)', 'Thời gian mạng (ms)'],
                'Fetch-and-Filter': [len(ff_results), f"{ff_nodes:,}", f"{ff_time*1000:.1f}", f"{ff_net_time*1000:.1f}"],
                'Fragment-First': [len(frag_results), f"{frag_nodes:,}", f"{frag_time*1000:.1f}", f"{frag_net_time*1000:.1f}"]
            })
            st.table(details_df)
            
            # Sample results
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

