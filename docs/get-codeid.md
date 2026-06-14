# 获取 CodeId 教程

本集成目前需要填写深圳燃气微信小程序请求头里的 `CodeId`。`CodeId` 一般长期不变，只需要获取一次；真正会定期过期的是接口 `access_token`，集成会自动刷新。

## 准备

推荐使用电脑上的微信和抓包工具获取。下面以 Charles / Proxyman / mitmproxy 这类工具为例，任选一个即可。

你需要准备：

- 电脑微信
- 一个 HTTPS 抓包工具
- 深圳燃气微信小程序已登录并绑定燃气账户

## 步骤

1. 打开抓包工具，并开启 HTTPS 解密。
2. 在电脑微信里打开“深圳燃气”小程序。
3. 进入账单、余额、用气记录等任意会加载账户数据的页面。
4. 在抓包工具里过滤域名：

   ```text
   wechat.szgas.com.cn
   ```

5. 找到任意 `/api/` 开头的请求。
6. 查看请求头，复制 `CodeId` 的值。

常见请求示例：

```text
https://wechat.szgas.com.cn/api/newcis/homepage/getBillDate
https://wechat.szgas.com.cn/api/handle/gasBill/getUserBillDataInfo
https://wechat.szgas.com.cn/api/handle/network/queryDayData
```

请求头里会有类似下面的字段：

```text
CodeId: xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

复制冒号后面的完整值，填入 Home Assistant 集成配置页的 `CodeId`。

## 注意事项

- 不要把 `CodeId` 发给别人，它可以访问你的燃气账户数据。
- `CodeId` 不是 OAuth token，通常不会频繁变化。
- 如果更换微信号、重新绑定深圳燃气账户，或小程序账号异常，可能需要重新获取。
- 如果抓包里看不到 HTTPS 内容，请确认抓包工具的根证书已经安装并信任。

## 为什么不能只填客户号？

深圳燃气的部分业务接口会校验 `CodeId`。实测同一个接口、同一个客户号：

- 不带 `CodeId`：返回缺少参数或页面加载失败。
- 带 `CodeId`：可以正常返回账单数据。

所以当前版本仍需要用户手动获取一次 `CodeId`。
