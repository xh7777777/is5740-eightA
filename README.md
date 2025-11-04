#### 字段说明（data/processed）
| 字段 | 含义 | 备注 |
| --- | --- | --- |
| ID | 订单唯一标识 | 数据清洗过程中保持原格式 |
| Delivery_person_ID | 配送员编号 | 可用于连接配送员属性表 |
| Delivery_person_Age | 配送员年龄 | 18–60 之外已清洗为缺失 |
| Delivery_person_Ratings | 配送员历史评分 | 取值范围 1–5 |
| Restaurant_latitude | 餐厅纬度 | 非法坐标已置为缺失 |
| Restaurant_longitude | 餐厅经度 | 非法坐标已置为缺失 |
| Delivery_location_latitude | 收货纬度 | 非法坐标已置为缺失 |
| Delivery_location_longitude | 收货经度 | 非法坐标已置为缺失 |
| Order_Date | 原始下单日期 | 字符串，含多种格式 |
| Time_Orderd | 原始下单时间 | 字符串，含 24:xx 等异常值 |
| Time_Order_picked | 原始取餐时间 | 字符串，含异常值 |
| Weather_conditions | 下单时天气 | Fog/Stormy 等分类 |
| Road_traffic_density | 路况拥堵程度 | Low/Medium/High/Jam |
| Vehicle_condition | 配送车辆状况评分 | 数值越高表示越好 |
| Type_of_order | 订单类型 | Meal/Snack/Drinks/Buffet |
| Type_of_vehicle | 配送工具类型 | motorcycle/scooter 等 |
| multiple_deliveries | 同时配送的订单数 | 0–3 之外清洗为缺失 |
| Festival | 是否节庆期 | Yes/No |
| City | 城市类型 | Urban/Metropolitan/Semi-Urban |
| Time_taken (min) | 实际配送总耗时（分钟） | 模型预测目标变量 |
| Time_Orderd_clean | 标准化后的下单时间（HH:MM） | 与 Time_Orderd 对应 |
| Time_Orderd_minutes | 下单时间转化为分钟数 | 方便序列建模 |
| Time_Order_picked_clean | 标准化后的取餐时间（HH:MM） | 与 Time_Order_picked 对应 |
| Time_Order_picked_minutes | 取餐时间转化为分钟数 | 方便计算时长 |
| Order_Date_clean | 标准化后的下单日期 | YYYY-MM-DD |
| order_to_pick_minutes | 下单到取餐耗时 | 包含跨日校正 |
| pickup_to_delivery_minutes | 取餐到送达耗时 | 对应末端配送阶段 |
| haversine_km | 餐厅到收货地直线距离（公里） | 仅存在于 featured 版本 |
| Order_dow | 下单星期几 | Monday–Sunday |
| Order_hour | 下单小时 | 0–23 |

#### 重要变量与初步洞察
- `Festival`：节日期间平均送达耗时 45.5 分钟，较平日（26.0 分钟）显著上升，应重点监控节庆日期的运力配置。
- `Road_traffic_density`：Jam 状态平均 31.2 分钟，是 Low 状态（21.3 分钟）的 1.5 倍，说明实时交通拥堵是影响效率的核心因素。
- `City`：Semi-Urban 区域平均耗时 49.7 分钟，远高于 Metropolitan（27.3 分钟），需要评估郊区资源布点与道路条件。
- `Weather_conditions`：Cloudy/Fog 条件下平均耗时约 28.9 分钟，相比 Sunny（21.9 分钟）延长 7 分钟，表明恶劣天气对效率有直接影响。
- `multiple_deliveries`：与配送总耗时的相关系数为 0.39，提示并单数量越多，送达延迟风险越高。
- `Delivery_person_Ratings` 与 `Vehicle_condition`：分别与耗时呈 -0.34 与 -0.23 的相关性，较高评分和更佳车辆状况有助于缩短配送时间，可作为人员与车辆管理指标。
- `pickup_to_delivery_minutes`：与总耗时高度相关（0.91），可拆分为可优化的末端配送阶段指标；相反，`haversine_km` 与总耗时几乎无线性关系，暗示距离不是当前瓶颈。
- 数据总量 45,584 单，整体平均耗时 26.3 分钟，90 分位为 40 分钟，可作为评估服务水平的基准线。

#### 数据清洗
  - data/raw/zomato_dataset.csv：20 列，未清洗的原始数据；包含异常时间（小数、24:xx、空值）、拼写
  错误的城市名称、评分/年龄越界值，缺失值未处理。
  - data/processed/zomato_deliveries_clean.csv：27 列，与原始行数相同；在原始字段基础上补
  齐清洗与派生列（Time_Orderd_clean, *_minutes, Order_Date_clean, order_to_pick_minutes,
  pickup_to_delivery_minutes 等），并完成城市纠正、缺失值/异常值处理及类型标准化。
  - data/processed/zomato_deliveries_featured.csv：30 列；全部保留 clean 数据，再新增建模特征如
  haversine_km（直线距离）、Order_dow（星期）、Order_hour（小时），方便做距离/时间维度的分析。
  - data/processed/zomato_deliveries_normalized.csv：27 列；字段与 clean 相同，但所有数值列经过
  MinMaxScaler 映射到 0–1 区间，用于需要无量纲输入的算法。

#### 与原始数据的主要差异

  - 缺失值：raw 中 Time_Orderd 各城市缺失率约 3–5%，clean 版已清洗/补齐并额外留存 _clean 列；
  normalized 同步使用补齐后的数据。
  - 异常值：clean/featured/normalized 统一剪裁年龄、评分与耗时的异常值，原始表中仍保留。
  - 派生特征：raw 缺少分钟数、跨日间隔、距离等工程化字段，clean 起开始提供时间差；featured 再增加
  距离与日期衍生维度；normalized 仅对 clean 的数值列做规模化。
  - 数据一致性：clean 及之后版本修正 Metropolitian 等拼写、去除重复行并保证时间单位统一；raw 保留
  原始状态。

#### 新增清洗逻辑
- 缺失值填充：`*_minutes` 与 `Time_taken (min)` 使用中位数，其他数值列按均值，分类列按众数补齐；计入 `issues` 统计。
- 异常值处理：对年龄、评分、时间耗时列应用 IQR 限幅，将极端值裁剪到四分位区间边界。
- 单位标准化：检测时间列是否混用秒，统一为分钟并上限 24 小时；距离列（含 `haversine_km`/`Delivery_distance` 等）统一转换为公里。
- 重复数据：先移除完全重复行，再按 `ID`/`Delivery_person_ID`/`Order_Date_clean` 组合保留最早记录。
- 归一化导出：清洗后的数据再生成一份 MinMax 归一化副本 `data/processed/zomato_deliveries_normalized.csv` ，供建模使用。


