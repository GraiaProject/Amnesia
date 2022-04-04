<div align="center">

# Amnesia

_A collection of common components for Graia Project._

> 于是明天仍将到来.

> 每一天都会带来新的邂逅, 纵使最终忘却也不会害怕明天到来.

</div>

<p align="center">
  <img alt="PyPI" src="https://img.shields.io/pypi/v/graia-amnesia" />
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="code_style" />
  <img src="https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336" />
  <a href="https://results.pre-commit.ci/latest/github/GraiaProject/Amnesia/master">
    <img src="https://results.pre-commit.ci/badge/github/GraiaProject/Amnesia/master.svg" />
  </a>

</p>

## 简述

Amnesia 是一系列共用组件的集合, 包含了以下内容:

 - 消息链 `MessageChain`, 沿袭自 Avilla 实现和 Ariadne 部分方法实现;
 - `Element` 基类和 `Text` 消息元素实现;
 - `Launch API`: 程序生命周期管理, 提供准备(`prepare`), 主线(`mainline`) 与 清理(`cleanup`) 三个时间节点; 支持依赖编排;
 - 轻量化实现的 `Service`;
 - 轻量化的内存缓存实现 `Memcache`, 原版本由 @ProgramRipper 实现, 沿袭自 Avilla;
 - `Transport API`: 职权分派, 交互主导的网络通信封装;
   - `uvicorn`: ASGI Runner;
   - `starlette`: ASGI Application;
   - `aiohttp`: Http & WebSocket Client.

通过 Amnesia, 我们希望能更加轻量化第三方库的依赖, 并籍此促进社区的发展.

 - `MessageChain` 可以让 Avilla, Ariadne, Alconna 等共用统一实现, 并使其泛用性扩大;
 - `Launch API` 可以优化应用的启动流程, 适用于 `Saya` 或是单纯的 `Broadcast Control` 应用;
 - `Service` 使维护和访问资源的流程更加合理;
 - ...或许还会有更多?

## 协议

本项目以 MIT 协议开源.
