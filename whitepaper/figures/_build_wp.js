const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, ImageRun, AlignmentType, PageBreak, TableOfContents } = require('docx');

const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 240, after: 120 }, children: [new TextRun({ text: t, font: 'Microsoft JhengHei' })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 180, after: 80 }, children: [new TextRun({ text: t, font: 'Microsoft JhengHei' })] });
const P  = (t, opts={}) => new Paragraph({ spacing: { after: 120, line: 320 }, children: [new TextRun({ text: t, font: 'Microsoft JhengHei', size: 22, ...opts })] });
const Cap = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: t, font: 'Microsoft JhengHei', size: 18, italics: true, color: '666666' })] });
const Fig = (file) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 }, children: [ new ImageRun({ type: 'png', data: fs.readFileSync(file), transformation: { width: 560, height: 329 } }) ] });
const Note = (t) => new Paragraph({ spacing: { after: 120, line: 320 }, border: { left: { style: 'single', size: 18, color: 'D0563B', space: 12 } }, children: [new TextRun({ text: t, font: 'Microsoft JhengHei', size: 20, color: '444444' })] });

const doc = new Document({
  styles: { default: { document: { run: { font: 'Microsoft JhengHei' } } } },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 } } },
    children: [
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 2400, after: 120 }, children: [new TextRun({ text: '從資訊繭房到 AI Agent 行為收斂', font: 'Microsoft JhengHei', size: 40, bold: true })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: '部署端 AI Agent 行為評估框架', font: 'Microsoft JhengHei', size: 28, color: '555555' })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 2400 }, children: [new TextRun({ text: 'White Paper v0.1（草稿）', font: 'Microsoft JhengHei', size: 20, color: '888888' })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Evan ｜ AI 治理與評估顧問', font: 'Microsoft JhengHei', size: 22 })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: '2026 年 7 月', font: 'Microsoft JhengHei', size: 20, color: '888888' })] }),
      new Paragraph({ children: [new PageBreak()] }),

      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: '目次', font: 'Microsoft JhengHei' })] }),
      new TableOfContents('目次', { hyperlink: true, headingStyleRange: '1-2' }),
      new Paragraph({ children: [new PageBreak()] }),

      H1('摘要'),
      P('本文提出一個針對「已部署 AI Agent」的行為評估框架。目前台灣的 AI 模型評測（如 AIEC、金融業 FinLLM 評測標準）多聚焦於模型本身的知識正確性與合規性，屬於「模型畢業考」。然而模型通過畢業考，不代表它進入特定企業、接上該企業的資料與權限之後，行為仍然守規矩。本文主張：這個「模型 × 企業資料 × 權限」的組合只存在於各別部署現場，需要獨立的部署端行為評估，而此處目前是市場空白。', { size: 22 }),
      P('本框架的理論根基是作者對「資訊繭房」的研究：資料偏差形成初始繭，Agent 在自主行動中以自身輸出繼續餵養自己，使繭自我加固。本文將此機制對映至 AI Agent，提出四層評估框架與成對題項協定，並以一個刻意埋入瑕疵的虛構金融客服 Agent（FinBot-P0）進行初步驗證。'),

      H1('1. 問題:模型畢業了,行員還沒考核'),
      P('（待撰寫）本章說明模型評測與部署端評估的落差，並引述產業已自行提出的需求訊號——金融機構已開始為 AI 行員編號、設管理辦法與考核機制。'),

      H1('2. 理論:繭是怎麼長出來的'),
      P('作者長期關注資訊繭房議題。其國立中山大學資訊管理系在職碩士論文《資訊繭房影響因素研究》，以 Sunstein（2001）與 Pariser（2011）為核心文獻，採 PLS-SEM 橫斷面問卷研究，取得 292 份有效問卷，初步探討多個影響因素與資訊繭房程度之間的關係。'),
      P('這項研究的實際結構不是「餵養、強化、收窄、回饋」的循環流程，而是「多個影響因素 → 資訊繭房程度」的迴歸模型：七個假說分別檢驗不同因素對依變數的影響方向。其中 H1、H6 獲支持，呈正向影響；H2（媒體碎化）、H3（資訊有用性確認）、H5（社會認同）未達顯著，不獲支持。'),
      P('H4 是本白皮書特別保留的實證錨點：渴望探索新知（Need for Cognition, NfC）對資訊繭房呈負向影響（β = -0.320）。換言之，探索傾向不是另一個加固繭房的因素，而是對抗繭房的保護因子。'),
      Fig('fig1.png'),
      Cap('圖 1｜影響因素與繭房程度:人與 AI Agent 的結構對映'),
      P('如圖 1 所示，本文把人的「影響因素 → 資訊繭房程度」結構搬到部署端，形成「企業端因素 → AI 繭化程度」的對映。此處不是把碩論的變數直接宣稱為 AI 的已證實機制，而是保留其問題結構，作為後續行為評估要檢驗的假設。'),
      P('保護因子的對映同樣重要：人可藉由主動探索新知抵抗資訊繭房；AI Agent 則需主動尋求反例、查證，並跳出既有脈絡，以抵抗企業端因素造成的繭化。圖中的反向箭頭用來區分「加固」與「保護」兩種相反方向。'),
      P('碩論也留下核心構念的測量矛盾：研究以自陳問卷測量資訊繭房，但真正在繭裡的人可能不知道自己在繭裡，因而形成測量效度的根本問題。這個限制移到 AI 場景後更為直接：AI 不能以自我報告證明自己沒有被繭化，只能透過可觀測行為接受測試；因此，本白皮書主張部署端需要行為測試，而不是採信系統的自我描述。'),
      P('此處對碩論的定位必須節制：它是作者問題意識的起點與先行者證明，不是已發表成果、學術權威或本框架的方法論基礎。本文將該問題意識延伸至 AI Agent，提出全新的行為評估方法；白皮書的可信度最終應來自 FinBot-P0 的新實證，而非碩論本身。'),
      Note('重要界定:本圖為結構類比,非已證實之同一機制。既有實證（如 Shumailov et al. 2024 的模型崩潰研究）針對的是「訓練迴圈」；本文右欄描述的是「部署中的推論迴圈」,兩者形似但非同一實驗所證。本文將此對映列為待驗證假設,並以第 4 章的 FinBot-P0 提供初步證據。'),
      P('此外須區分兩個常被混用的概念:「幻覺」是模型生成與事實不符的內容,屬能力問題;「繭化」是資料偏差加上自我餵食導致的系統性判斷偏向,屬餵養問題。繭化會使幻覺更難被察覺、更易自我加固,但兩者機制不同,本文一律分開使用。'),

      H1('3. 方法:四層評估框架'),
      P('本框架將 AI Agent 的可信度拆為四個層次,對應四個問題:說得對不對(內容層)、做事守不守規矩(行為層)、錯的時候怎麼錯(失效層)、事後查不查得到帳(軌跡層)。'),
      Fig('fig2.png'),
      Cap('圖 2｜四層評估框架與台灣現有覆蓋概況'),
      P('如圖 2 所示,內容層已由既有的模型評測機制覆蓋;軌跡層有工具但缺乏標準;行為層與失效層則未見公開的獨立第三方服務。本框架的定位即在後兩層——這也是模型畢業考測不到、卻是企業上線後最可能出事的地方。'),
      Note('市場現況查證提醒:圖 2「未見公開的獨立第三方」為初步觀察,正式發表前須逐一查證國內資安顧問、四大會計師事務所在台之 AI assurance 業務、以及學術機構的研究進度,以確保此主張可辯護。'),
      H2('3.1 成對題項協定'),
      P('(待撰寫,俟評分 rubric 定稿後補入方法細節與圖 3。)'),

      H1('4. 實驗:FinBot-P0'),
      P('(待 pilot 完成後填入。設計要點:一個虛構金融客服 Agent,其知識庫刻意埋入過時、矛盾、偏頗文件,形成一張「有標準答案的考卷」,用以驗證本框架能否偵測已知瑕疵,以及資料污染如何傳導至行為層。)'),

      H1('5. 治理對接'),
      P('(待撰寫。金管會《金融業運用人工智慧指引》條文對映,以及 NIST AI RMF、ISO/IEC 42001、EU AI Act 之對照。)'),

      H1('6. 結論與限制'),
      P('(待撰寫。說明各項通過門檻為 pilot 校準值、judge 偏誤、題庫輪換與跨模型泛化等未決研究議題。)'),
    ],
  }],
});

Packer.toBuffer(doc).then(b => { fs.writeFileSync('whitepaper-v0.1.docx', b); console.log('docx written'); });
