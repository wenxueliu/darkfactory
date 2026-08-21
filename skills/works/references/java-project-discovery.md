# Java 项目定位

从 `--project` 根目录开始，依据以下信号识别实际 Java 项目和模块边界：

- `pom.xml`、`build.gradle`、`build.gradle.kts`
- `mvnw`、`mvnw.cmd`、`gradlew`、`gradlew.bat`
- `src/main/java`、`src/test/java`
- Maven modules 或 Gradle multi-project 声明

不要假定候选项目的目录名。搜索时排除 `.git`、`target`、`build`、生成代码和依赖缓存。读取目标目录适用的项目指令，再为每个功能点定位：

1. 所属模块和构建入口。
2. 必须修改的已有类和已有方法。
3. 上下游调用方、接口和实现类。
4. 相关已有测试、fixture 与配置。
5. 可能受影响的兼容行为和回归面。

只有定位证据表明不存在合适的存量入口时，才考虑新增生产类。
