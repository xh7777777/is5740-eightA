#### 数据清洗
City：拼写纠正；转 category。

所有字符串列：去空格、标准缺失值处理。

Time_Orderd, Time_Order_picked：小数→HH:MM、HH:MM:SS截短、24:xx截断、失败置 NA；派生 _clean 与 _minutes。

Order_Date：按 DD-MM-YYYY 解析 → Order_Date_clean。

Delivery_person_Age：不在 18–60 置 NA。

Delivery_person_Ratings：不在 1–5 置 NA。

multiple_deliveries：非 {0,1,2,3} 置 NA。

四个经纬度列：0 → NA。

依赖上述字段派生：order_to_pick_minutes、pickup_to_delivery_minutes（含跨日与负值处理）。

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
