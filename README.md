# PINN 热方程求解器

基于物理信息神经网络（Physics-Informed Neural Networks, PINN）的热方程数值求解Web应用。

## 项目简介

本项目实现了一个使用物理信息神经网络求解一维热方程的Web应用程序。通过神经网络学习热传导问题的物理规律，结合边界条件和初始条件进行训练，最终得到热方程的数值解。

### 热方程

$$\frac{\partial u}{\partial t} = \alpha \frac{\partial^2 u}{\partial x^2}$$

其中：
- $u(x,t)$ 表示位置 $x$ 在时刻 $t$ 的温度
- $\alpha$ 为热扩散系数

### 解析解

对于初始条件 $u(x,0) = \sin(\pi x)$ 和边界条件 $u(0,t) = u(1,t) = 0$，解析解为：

$$u(x,t) = e^{-\alpha \pi^2 t} \sin(\pi x)$$

## 功能特性

- ✅ 参数可调：热扩散系数 $\alpha$、学习率、训练轮数、隐藏层神经元数
- ✅ 实时训练：多线程后台训练，支持随时停止
- ✅ 训练可视化：实时显示损失函数变化曲线
- ✅ 结果可视化：
  - 温度场分布云图
  - 3D温度曲面图
  - 不同时间点的温度曲线对比
  - 误差热力图
  - 边界条件验证图
- ✅ 数值对比：PINN预测值与解析解的对比
- ✅ 交互式Web界面

## 技术栈

- **后端**：Python + Flask + NumPy
- **前端**：HTML5 + Bootstrap 5 + JavaScript
- **可视化**：Matplotlib
- **优化算法**：梯度下降法（有限差分计算导数）

## 项目结构

```
pinn-parabolic-equation/
├── pinn_web.py          # Flask主程序
├── templates/
│   └── index.html       # Web前端界面
├── README.md            # 项目说明
└── documentation.pdf    # 详细说明文档
```

## 快速开始

### 环境要求

- Python 3.8+
- Flask
- NumPy
- Matplotlib

### 安装依赖

```bash
pip install flask numpy matplotlib
```

### 运行应用

```bash
python pinn_web.py
```

然后在浏览器中打开 http://localhost:8081

### 使用说明

1. **参数设置**
   - 热扩散系数 $\alpha$：默认0.01，范围0.001-1
   - 学习率：默认0.01，范围0.0001-0.1
   - 训练轮数：默认100，范围10-1000
   - 隐藏神经元数：默认4，范围2-20

2. **开始训练**
   - 点击"开始训练"按钮启动训练过程
   - 可以随时点击"停止训练"按钮中断训练
   - 训练过程中可以查看实时损失曲线

3. **查看结果**
   - 训练完成后自动显示各种可视化结果
   - 可以查看预测值与解析解的对比
   - 表格显示具体数值对比

## 神经网络架构

本项目使用一个简单的前馈神经网络：

- 输入层：2个神经元（$x$, $t$）
- 隐藏层：可配置神经元数量（默认4个），激活函数为 $\tanh$
- 输出层：1个神经元（$u(x,t)$）

### 损失函数

总损失由两部分组成：

$$L = L_{boundary} + L_{physics}$$

- **边界损失** $L_{boundary}$：强制网络满足边界条件和初始条件
- **物理损失** $L_{physics}$：强制网络满足热方程物理规律

$$L_{physics} = \frac{1}{N}\sum_{i=1}^{N}\left(\frac{\partial u}{\partial t} - \alpha\frac{\partial^2 u}{\partial x^2}\right)^2$$

## 许可证

MIT License

## 作者

shwsq

PINN热方程求解器 - 基于物理信息神经网络的科学计算应用
