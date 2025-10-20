import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px

# 页面配置
st.set_page_config(
    page_title="户用光伏储能系统优化计算器",
    page_icon="🔋",
    layout="wide"
)

# 应用标题
st.title("🔋 户用光伏储能系统优化计算器")
st.markdown("""
本应用用于优化家庭光伏发电系统和储能系统的配置，采用光伏组件+混合逆变器+储能电池方案，
策略为**最大化光伏发电利用率**并**减少电网用电**。
""")

# 预设组件参数
PV_COMPONENTS = {
    "隆基Hi-MO 5": {"efficiency": 21.3, "price_per_w": 2.5},
    "晶科Tiger Pro": {"efficiency": 20.9, "price_per_w": 2.3},
    "天合至尊": {"efficiency": 21.6, "price_per_w": 2.6},
    "阿特斯BiHiKu": {"efficiency": 21.4, "price_per_w": 2.6},
    "自定义组件": {"efficiency": 20.0, "price_per_w": 2.0}
}

# 侧边栏 - 用户输入
with st.sidebar:
    st.header("系统参数设置")

    # 用户基本信息
    st.subheader("家庭用电信息")
    monthly_usage = st.number_input("月均用电量 (kWh)", min_value=100, max_value=2000, value=500)
    peak_usage = st.number_input("高峰时段用电比例 (%)", min_value=10, max_value=90, value=60)
    backup_hours = st.number_input("备用电量时长 (小时)", min_value=1, max_value=24, value=4)

    # 光伏系统参数
    st.subheader("光伏系统参数")
    sunshine_hours = st.number_input("当地日均有效日照小时数", min_value=1.0, max_value=8.0, value=4.5, step=0.1)
    system_loss = st.number_input("系统损耗 (%)", min_value=5, max_value=30, value=15)

    # 选择光伏组件
    pv_component = st.selectbox("选择光伏组件类型", list(PV_COMPONENTS.keys()))
    pv_power_per_panel = st.number_input("单块组件功率 (W)", min_value=100, max_value=800, value=450)
    pv_count = st.number_input("光伏组件数量", min_value=1, max_value=100, value=20)

    # 储能系统参数
    st.subheader("储能系统参数")
    battery_capacity = st.number_input("电池容量 (kWh)", min_value=1.0, max_value=50.0, value=10.0, step=0.5)
    battery_efficiency = st.number_input("电池效率 (%)", min_value=80, max_value=99, value=95)
    dod_limit = st.number_input("电池放电深度 (%)", min_value=50, max_value=100, value=90)

    # 逆变器参数
    st.subheader("逆变器参数")
    inverter_power = st.number_input("逆变器功率 (kW)", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
    inverter_efficiency = st.number_input("逆变器效率 (%)", min_value=90, max_value=99, value=98)
    inverter_price = st.number_input("逆变器价格 (元)", min_value=5000, max_value=30000, value=10000)

    # 经济性参数
    st.subheader("经济性参数")
    electricity_price = st.number_input("电价 (元/kWh)", min_value=0.3, max_value=2.0, value=0.6)
    subsidy = st.number_input("政府补贴 (元/kWh)", min_value=0.0, max_value=1.0, value=0.3)
    feed_in_tariff = st.number_input("上网电价 (元/kWh)", min_value=0.0, max_value=1.0, value=0.2)

# 获取组件参数
pv_params = PV_COMPONENTS[pv_component]
pv_power_kw = pv_power_per_panel / 1000  # 转换为kW


# 计算系统参数
def calculate_system():
    # 光伏系统总容量
    pv_total_power = pv_power_kw * pv_count  # kW

    # 日均发电量
    daily_generation = pv_total_power * sunshine_hours * (pv_params["efficiency"] / 100) * (1 - system_loss / 100)

    # 储能系统可用容量
    usable_capacity = battery_capacity * (dod_limit / 100)

    return {
        "光伏总功率(kW)": round(pv_total_power, 2),
        "日均发电量(kWh)": round(daily_generation, 2),
        "电池容量(kWh)": round(battery_capacity, 2),
        "可用容量(kWh)": round(usable_capacity, 2),
        "逆变器功率(kW)": inverter_power
    }


# 能量流模拟
def simulate_energy_flow(system_params):
    # 日均用电量
    daily_usage = monthly_usage / 30

    # 高峰时段用电量
    peak_usage_kwh = daily_usage * peak_usage / 100

    # 模拟一天24小时的能量流动
    hours = 24
    time = list(range(hours))

    # 发电曲线 (正弦曲线模拟)
    generation = [0] * hours
    for h in range(6, 19):  # 6:00-18:00有光照
        # 正弦曲线模拟发电量变化
        normalized_hour = (h - 6) / 12
        generation[h] = system_params["日均发电量(kWh)"] * np.sin(normalized_hour * np.pi) * 0.5

    # 用电曲线 (双峰曲线)
    consumption = [0] * hours
    for h in range(hours):
        # 基础用电 + 高峰时段增加
        base_load = daily_usage / hours
        if 7 <= h <= 10 or 18 <= h <= 22:  # 早晚高峰
            consumption[h] = base_load * 1.8
        else:
            consumption[h] = base_load

    # 电池状态
    battery_soc = [0] * hours  # 电池电量
    grid_import = [0] * hours  # 从电网购电
    grid_export = [0] * hours  # 向电网售电
    battery_charge = [0] * hours  # 电池充电
    battery_discharge = [0] * hours  # 电池放电

    current_soc = 0  # 初始电量为0
    usable_capacity = system_params["可用容量(kWh)"]

    for h in range(hours):
        # 计算净发电量
        net_generation = generation[h] - consumption[h]

        if net_generation > 0:  # 发电量大于用电量
            # 多余电量先给电池充电
            max_charge = min(net_generation, (usable_capacity - current_soc) / (battery_efficiency / 100))
            battery_charge[h] = max_charge
            current_soc += max_charge * (battery_efficiency / 100)

            # 如果还有多余电量，卖给电网
            remaining = net_generation - max_charge
            if remaining > 0:
                grid_export[h] = remaining
        else:  # 用电量大于发电量
            deficit = -net_generation

            # 先用电池放电
            max_discharge = min(deficit, current_soc * (battery_efficiency / 100))
            battery_discharge[h] = max_discharge
            current_soc -= max_discharge / (battery_efficiency / 100)

            # 如果还有不足，从电网购电
            remaining_deficit = deficit - max_discharge
            if remaining_deficit > 0:
                grid_import[h] = remaining_deficit

        battery_soc[h] = current_soc

    return {
        "时间": time,
        "发电量": generation,
        "用电量": consumption,
        "电池电量": battery_soc,
        "电网购电": grid_import,
        "电网售电": grid_export,
        "电池充电": battery_charge,
        "电池放电": battery_discharge
    }


# 经济性分析
def economic_analysis(system_params, energy_flow):
    # 初始投资
    pv_investment = pv_count * pv_power_per_panel * pv_params["price_per_w"]
    battery_investment = battery_capacity * 1000  # 假设每kWh成本1000元
    inverter_investment = inverter_price
    total_investment = pv_investment + battery_investment + inverter_investment

    # 年发电量
    annual_generation = system_params["日均发电量(kWh)"] * 365

    # 年用电量
    annual_consumption = monthly_usage * 12

    # 年电网购电量
    annual_grid_import = sum(energy_flow["电网购电"]) * 365 / 24

    # 年电网售电量
    annual_grid_export = sum(energy_flow["电网售电"]) * 365 / 24

    # 年收益计算
    # 节省电费 = (总用电量 - 电网购电量) * 电价
    saving_from_self_use = (annual_consumption - annual_grid_import) * electricity_price

    # 售电收益
    income_from_export = annual_grid_export * feed_in_tariff

    # 补贴收益
    subsidy_income = annual_generation * subsidy

    total_annual_benefit = saving_from_self_use + income_from_export + subsidy_income

    # 简单投资回收期
    payback_years = total_investment / total_annual_benefit if total_annual_benefit > 0 else float('inf')

    return {
        "光伏投资(元)": round(pv_investment),
        "储能投资(元)": round(battery_investment),
        "逆变器投资(元)": round(inverter_investment),
        "总投资(元)": round(total_investment),
        "年发电量(kWh)": round(annual_generation),
        "年自用电量(kWh)": round(annual_consumption - annual_grid_import),
        "年购电量(kWh)": round(annual_grid_import),
        "年售电量(kWh)": round(annual_grid_export),
        "年总收益(元)": round(total_annual_benefit),
        "投资回收期(年)": round(payback_years, 1) if payback_years != float('inf') else ">50年"
    }


# 计算备用供电能力
def calculate_backup_capacity(system_params):
    # 日均用电量
    daily_usage = monthly_usage / 30

    # 高峰时段用电量
    peak_usage_kwh = daily_usage * peak_usage / 100

    # 可用储能容量
    usable_capacity = system_params["可用容量(kWh)"]

    # 备用供电时长
    backup_capacity_hours = usable_capacity / (peak_usage_kwh / backup_hours)

    return backup_capacity_hours


# 主计算逻辑
system_params = calculate_system()
energy_flow = simulate_energy_flow(system_params)
economics = economic_analysis(system_params, energy_flow)
backup_capacity = calculate_backup_capacity(system_params)

# 结果显示
st.subheader("系统配置概览")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("光伏组件", f"{pv_component} × {pv_count}")
    st.metric("总功率", f"{system_params['光伏总功率(kW)']} kW")
    st.metric("日均发电量", f"{system_params['日均发电量(kWh)']} kWh")

with col2:
    st.metric("储能系统", f"{battery_capacity} kWh")
    st.metric("可用容量", f"{system_params['可用容量(kWh)']} kWh")
    st.metric("备用供电时长", f"{round(backup_capacity, 1)} 小时")

with col3:
    st.metric("逆变器功率", f"{inverter_power} kW")
    st.metric("逆变器效率", f"{inverter_efficiency}%")
    st.metric("系统损耗", f"{system_loss}%")

# 经济性分析
st.subheader("经济性分析")
econ_df = pd.DataFrame.from_dict(economics, orient='index', columns=['数值'])
st.dataframe(econ_df, use_container_width=True)

# 能量流可视化
st.subheader("24小时能量流模拟")
df_energy = pd.DataFrame({
    "时间": energy_flow["时间"],
    "发电量(kWh)": energy_flow["发电量"],
    "用电量(kWh)": energy_flow["用电量"],
    "电池电量(kWh)": energy_flow["电池电量"],
    "电网购电(kWh)": energy_flow["电网购电"],
    "电网售电(kWh)": energy_flow["电网售电"],
    "电池充电(kWh)": energy_flow["电池充电"],
    "电池放电(kWh)": energy_flow["电池放电"]
})

# 创建堆叠面积图展示能量流
fig_energy = px.area(df_energy, x="时间", y=["发电量(kWh)", "用电量(kWh)", "电网购电(kWh)", "电网售电(kWh)"],
                     title="24小时能量流动模拟")
st.plotly_chart(fig_energy, use_container_width=True)

# 电池状态可视化
fig_battery = px.area(df_energy, x="时间", y=["电池电量(kWh)"],
                      title="电池充放电状态")
st.plotly_chart(fig_battery, use_container_width=True)

# 组件参数参考
st.subheader("光伏组件参数参考")
pv_df = pd.DataFrame.from_dict(PV_COMPONENTS, orient='index')
st.dataframe(pv_df, use_container_width=True)

# 部署说明
st.subheader("部署到Streamlit Sharing")
st.markdown("""
1. 将本代码保存为 `pv_storage_optimizer.py`
2. 上传到GitHub仓库
3. 登录[Streamlit Sharing](https://share.streamlit.io/)
4. 选择仓库和文件进行部署
""")

# 添加样式
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .stMetric label {
        font-size: 1rem;
        color: #666;
    }
    .stMetric div {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
    }
    .css-1v0mbdj {
        border-radius: 10px;
        overflow: hidden;
    }
    .stDataFrame {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)
