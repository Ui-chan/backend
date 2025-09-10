# 자폐 스펙트럼 장애(ASD) 아동을 위한 ESDM 기반 디지털 치료 게임

해당 프로젝트는 **자폐 스펙트럼 장애(ASD) 아동**을 위해 설계된 양방향 디지털 치료 게임입니다.  
조기 개입 덴버 모델(ESDM) 원칙을 기반으로, 가정 환경에서 아동의 사회성, 인지, 의사소통 기술 발달을 지원하기 위한 **흥미로운 게임 기반 중재 프로그램**을 제공합니다.

---

# 🌟 프로젝트 소개

자폐 스펙트럼 장애(ASD)의 유병률은 꾸준히 증가하여 최근 몇 년간 3%를 넘어섰습니다.  
연구에 따르면 조기 개입은 아동의 뇌 가소성이 높은 시기를 활용하여 장기적인 발달 지연을 줄이고, 언어, 인지, 일상생활 기술을 향상시키는 데 매우 중요합니다.

이 프로젝트는 **부모와 아동이 함께 사용할 수 있는 효과적이고 접근성 높은 치료 도구**를 제공하기 위해 개발되었습니다.  
저희의 목표는 **만 2세에서 4세 사이의 자폐 진단 아동**이 가정에서도 부모와 함께 게임을 통해 치료를 받고, 증상을 완화할 수 있도록 지원하는 것입니다.  

이를 통해 병원 중심의 치료 환경을 보완하고, **가정 내에서도 지속적이고 즐거운 치료 경험**을 제공하는 것을 목표로 하고 있습니다.

**개발 기간**: 3달


# 🛠️ 백엔드 기술 스택 – Zerodose_ASD

|  | 기술 스택 |
| :---: | :----------------------------- |
| 언어 | <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"> |
| 라이브러리 | <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white"> <img src="https://img.shields.io/badge/boto3-4B8BBE?style=for-the-badge&logo=python&logoColor=white"> |
| DB | <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white"> |
| 클라우드/인프라 | <img src="https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white"> <img src="https://img.shields.io/badge/Vertex_AI-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white"> <img src="https://img.shields.io/badge/Gemini-000000?style=for-the-badge&logo=google&logoColor=white"> <img src="https://img.shields.io/badge/AWS_S3-232F3E?style=for-the-badge&logo=amazonaws&logoColor=white"> |



---

# 👥 팀원 소개


<table>
  <tbody>
    <tr align="center">
      <td><img src="https://avatars.githubusercontent.com/u/66213259?v=4" width="100px;" alt="안의찬"/><br />안의찬</td>
      <td><img src="https://avatars.githubusercontent.com/u/89250962?v=4" width="100px;" alt="강서영"/><br />강서영</td>
      <td><img src="https://avatars.githubusercontent.com/u/108521560?v=4" width="100px;" alt="홍석호"/><br />홍석호</td>
      <td><img src="https://avatars.githubusercontent.com/u/78317343?v=4" width="100px;" alt="안경철"/><br />안경철</td>
    </tr>
    <tr align="center">
      <td><a href="https://github.com/Ui-chan">PM / FE / BE</a></td>
      <td><a href="https://github.com/KangSY01">BE</a></td>
      <td><a href="https://github.com/possibilitas">FE</a></td>
      <td><a href="https://github.com/GANG701">FE</a></td>
    </tr>
  </tbody>
</table>

---

# ✨ 주요 기능 – 게임 소개

| 게임 이름 | 목표/기능 | 설명 | 이미지 |
| :---: | :--- | :--- | :--- |
| Look Over There! | 공동 주시 (Joint Attention) | 부모가 가리키는 사물을 아동이 함께 바라보게 하여 공동 주시 능력을 향상시킵니다. Vertex AI를 활용하여 새로운 이미지를 동적으로 생성함으로써 콘텐츠를 신선하고 흥미롭게 유지합니다. | <img width="1640" height="2360" alt="IMG_0200" src="https://github.com/user-attachments/assets/394487f8-ade8-488c-9605-7666d865b07f" /> |
| Copy the Face | 사회적 모방 및 감정 | 얼굴 표정을 이해하고 모방하게 하여 사회적 모방 및 감정 인식 기술 발달을 돕습니다. Google Cloud Vision API를 통합하여 아동의 표정을 인식하고 긍정적인 피드백을 제공합니다. | <img width="1640" height="2360" alt="IMG_0172" src="https://github.com/user-attachments/assets/c3e8b437-3ac0-4e97-b98e-38a905a6f9f0" /> |
| Ball Toss | 상호작용적 차례 주고받기 | 간단하고 재미있는 가상 공 던지기 게임을 통해 상호작용 및 차례 주고받기의 기본을 학습합니다. 캐릭터의 긍정적인 반응이 지속적인 참여를 유도하는 강화 학습 원리를 사용합니다. | <img width="1640" height="2360" alt="IMG_0173" src="https://github.com/user-attachments/assets/8569de00-7417-49bd-b1de-8a377f053bc1" /> |
| I Want This! | 기능적 의사소통 (FCT) | 아동이 보고 싶은 것을 직접 선택하게 하여 기능적 의사소통 및 선택 결정 능력을 발달시킵니다. 효과적인 의사소통 방법을 가르쳐 문제 행동을 줄이는 기능적 의사소통 훈련(FCT)을 기반으로 합니다. | <img width="1640" height="2360" alt="IMG_0174" src="https://github.com/user-attachments/assets/9a2049df-e364-409a-a9af-5e782cfcb729" /> |

# ✨ 부모 페이지 – 주요 기능

| 기능 이름 | 목표/기능 | 설명 | 이미지 |
| :---: | :--- | :--- | :--- |
| Main Dashboard | 아동 데이터 분석 & 서비스 | 아동의 게임 데이터를 기반으로 **주간 AI 분석**을 제공하고, 다양한 맞춤형 서비스에 접근할 수 있는 메인 페이지입니다. | <img width="1640" height="2360" alt="IMG_0232" src="https://github.com/user-attachments/assets/79a0ccb1-ccdb-4db7-aa27-d87d12ed218e" /> |
| Analysis Page | 게임별 결과 시각화 | 각 게임에서 아동이 수행한 결과 데이터를 **시각적 그래프**로 제공하여 발달 변화 추이 확인 및 게임별 AI 분석 제공 할 수 있습니다. | <img width="1640" height="2360" alt="IMG_0233" src="https://github.com/user-attachments/assets/48c02950-9929-467d-b719-7f1044a168f2" /> |
| ASD Screening | ASD 진단표 | 실제 ASD 진단 아동을 대상으로 한 **중요 요소 기반 진단표**를 제공하여 부모가 아동의 특성을 간단히 평가할 수 있도록 지원합니다. | <img width="1640" height="2360" alt="IMG_0234" src="https://github.com/user-attachments/assets/f701abc9-04fc-4b1a-9dbc-91b97510fc7e" /> |
| Parent Education | 부모 교육 자료 | ASD 관련 영상, 블로그, 자료를 제공하여 부모가 **치료 및 상호작용 방법**을 학습하고 지원할 수 있는 페이지입니다. | <img width="1640" height="2360" alt="IMG_0236" src="https://github.com/user-attachments/assets/c8178c69-bdcf-4904-ac73-db20a84af6a4" /> |

# 📢 포스트 및 발표 자료 (Posts & Presentations)
## 📄 학회 발표: EKC 2025

- **학회**: EKC 2025 (Europe-Korea Conference on Science and Technology)  
- **발표 제목**: Digital Early Intervention with ESDM: A Serious Game for ASD  

**관련 링크**:  
- [PPT 자료 보기](https://www.canva.com/design/DAGykN0AffM/5A7XiPBt_ZU9-kAOdcf0_Q/edit?utm_content=DAGykN0AffM&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)  

**포스터 자료**:  
<img width="600px" alt="EKC 포스터" src="https://github.com/user-attachments/assets/53532ebb-a7f9-47f4-8f09-d80ebc87e36e" />
