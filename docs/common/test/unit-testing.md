# 单元测试

> 来源：`docs/common/单元测试.pdf`（共 28 页）
> 说明：保留全部文字与表格；原 PDF 中的截图、示意图未纳入。

专业课综合实训III 单元测试 童浩楠 hntong@bjtu.edu.cn 软件学院

## 目录

1. 什么是单元测试？

2. 单元测试工具JUnit

3. 测试覆盖率分析

1. 什么是单元测试？

2. 单元测试工具JUnit

3. 测试覆盖率分析

## 单元测试

- 单元测试是针对最小的功能单元进行测试
- 单元测试包括静态单元测试和动态单元测试
- Java程序中最小的功能单元一般认为是方法，因此对Java程序的单元测试就是针对Java类中单个方法的测试

## 单元测试框架

- 使用main()方法手动测试的缺点：
  - 只有一个main()方法，不能把测试代码分离
  - 繁琐枯燥，很难实现自动化测试
- 使用单元测试框架的好处：
  - 确保单个方法能够运行
  - 可以实现自动化运行所有测试用例并获得测试报告

## 目录

1. 什么是单元测试？

2. 单元测试工具

3. 测试覆盖率分析

## 单元测试工具

- JUnit是一个针对Java语言的主流单元测试框架
- PyTest是一个针对Python语言的第三方的主流单元测试框架

## JUnit

- JUnit是一个针对Java语言的单元测试框架，由Kent Beck和Erich Gamma共同建立，逐渐成为源于Kent Beck的xUnit家族中最为成功的一个。

Kent Beck Erich Gamma

极限编程，测试驱动开发创始人 Eclipse之父、Junit作者Junit作者

- 常用的IDE都集成了JUnit

Intellij IDEA

- 多个不同版本，最新版本为JUnit5 ，常用的是JUnit4 https://junit.org/junit5/ (JDK>=1.8)

https://junit.org/junit4/ (JDK>=1.5)

- Eclipse项目中安装JUnit
  - 在项目上右键→Properties → java build path → Libraries → 选择Classpath →点击Add External JARs/Add Libraries → Junit →选择版本
- JUnit基本概念
  - TestCase：代表一个测试用例，每一个TestCase实例都对应一个测试，这个测试通过这个TestCase实例的名字进行标识，以便在测试结果中指明哪个测试出现了问题；
  - TestSuite：测试套件，代表需要测试的一组测试用例；
  - TestFixtrue：代表一个测试环境。它用于组合一组测试用例，这组测试用例需要共同的测试运行环境；
  - TestResult：用于收集测试结果；
  - TestRunner: 用于执行/运行测试用例；
  - TestListener：用于监听测试过程；
  - Assert：用于断言测试结果是否正确；
- Junit常用断言
  - assertEquals([String message], expected, actual) ：断言expected参数和actual参数是否相等，假如不相等，则验证失败。
  - assertEquals([String message], expected, actual, tolerance) ：针对浮点型数据，断言expected参数和actual参数是否相等，tolerance是误差参数，参加比较的两个浮点数在这个误差之内则会被认为是相等的。
  - assertTrue ([String message], Boolean condition)：断言给定的布尔型值是否为真，假如结果为假，则验证失败。
  - assertNull([String message], Object object) ：断言给定的对象是否为null，假如不为null，则验证失败。
  - assertSame ([String message], expected, actual)：断言验证expected参数和actual参数所引用的是否是同一个对象，假如不是，则验证失败。

## Junit使用

- 一段Java程序
  - 计算数字求和字符串的和，比如，输入“1+2+3”，输出6
- 创建Test文件夹，专门存放单元测试相关内容
  - 选中项目，右键→New → Source Folder →Folder Name：Test
- 利用Junit进行单元测试
  - 选中被测文件→New →Junit Test Case →配置Source Folder为Test
- 利用Junit进行单元测试
  - 会自动生成一个类名为“Test”的类
- 利用Junit进行单元测试
  - 会自动生成一个类名为“Test”的类，接着在该类中添加测试用例代码
- 单元测试结果
  - 点击运行按钮，运行测试用例
- 单元测试结果
  - 左侧面板会显示运行结果（绿色-通过，红色-不通过）
    - Runs：执行的测试用例数目/

测试用例总数

    - Failures：断言不通过
    - Errors: 未到断言，程序终止
- 注解 @Before 的用途 —— 节省代码
- 注解 @Before 的用途 —— 节省代码

## 目录

1. 什么是单元测试？

2. 单元测试工具JUnit

3. 测试覆盖率分析

## 测试覆盖率分析

- 基础知识——逻辑覆盖及测试覆盖率

路径覆盖 条件组合覆盖 MC/DC 条件判定覆盖 判断覆盖 语句覆盖 条件覆盖

- 常见JAVA单元测试覆盖率工具
  - Emma：较老
  - JaCoCo：Emma的替代品，可看作Emma的升级版， 提供Eclipse插件；
  - Eclemma：Eclipse插件，eclemma2.0之前采用Emma，之后采用JaCoCo；
  - Cobertura, Mockito等。

## 测试覆盖率工具

- JaCoCo生成测试覆盖率报告

JaCoCo是从代码指令（Instructions， Coverage），分支（Branches， Coverage），圈复杂度（Cyclomatic Complexity），行（Lines），方法（Methods），类（Classes）等维度进行覆盖率分析。

- JaCoCo代码覆盖详情
  - 绿色代表已执行
  - 红色代表未执行
  - 黄色代表执行了一部分
- Coverage是一个面向Python程序的第三方测试覆盖率衡量工具
- https://coverage.readthedocs.io/en/latest/
