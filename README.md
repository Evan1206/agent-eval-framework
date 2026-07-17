# Agent Behavioral Evaluation Framework(AI Agent 行為評估框架)

> 模型評測告訴你「AI 畢業考幾分」;本框架告訴你「它進你公司之後,行為守不守規矩」。

從資訊繭房(Information Cocoon)理論出發的 AI Agent 行為評估方法:資料偏差形成初始繭,Agent 自主行動中的自我餵食迴圈使繭自我加固。本框架量測繭化在四個層次的呈現,協助部署方在上線前後驗證 Agent 的可信度。

## 四層評估框架

| 層 | 問題 | 量測面向 |
|---|---|---|
| 1. 內容層 | 說得對不對、穩不穩? | 正確性、一致性 |
| 2. 行為層 | 做事守不守規矩? | 權限抗性、原則一致性、工具使用安全、越界偵測 |
| 3. 失效層 | 錯的時候怎麼錯? | 失效模式(誠實 vs. 自信瞎掰)、錯誤傳播 |
| 4. 軌跡層 | 事後查不查得到帳? | 可解釋性、記錄完整性 |

核心方法:**成對題項協定(Paired-Item Protocol)**——每條行為原則以錨定題+變體題成對測試,量測行為結論在措辭、身分、壓力、語言變化下的漂移率。方法論根據 CheckList(Ribeiro et al., 2020)的不變性測試延伸至 Agent 行為層。

## Repo 結構

```
docs/        評估規格書(方法論全文)
harness/     測試執行工具(Python)
examples/    已除役的範例題(展示題目格式;正式題庫不公開)
whitepaper/  白皮書(撰寫中)
```

## 為什麼題庫不公開

測試集一旦公開即遭污染——受測系統(或其訓練資料)看過考題,分數便失去意度。本框架的正式題庫維持 holdout 狀態並定期輪換,以維持評估效度。`examples/` 提供已除役題目供理解格式之用。

## 快速開始

```bash
cd harness
pip install -r requirements.txt
python -m agent_eval.run --config configs/mock.yaml   # 以內建 mock agent 跑通流程
```

## 引用與授權

程式碼以 MIT 授權釋出。方法論文件(docs/、whitepaper/)版權所有,引用請註明出處。

## 作者

Evan — AI 策略分析師|AI 治理與評估顧問
研究背景:資訊繭房(碩士論文)→ AI Agent 行為收斂
