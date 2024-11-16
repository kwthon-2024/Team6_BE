from selenium import webdriver
from selenium.webdriver.common.by import By
import time

# 웹 드라이버 설정
driver = webdriver.Chrome()  # Chrome 드라이버 경로 설정 필요

# 로그인 페이지로 이동
driver.get("https://klas.kw.ac.kr/usr/cmn/login/LoginForm.do")

time.sleep(2)

# 로그인 정보 입력
driver.find_element(By.ID, "loginId").send_keys("2024404060")
driver.find_element(By.ID, "loginPwd").send_keys("asdf0422!")

time.sleep(1)

# 로그인 버튼 클릭
driver.find_element(
    By.XPATH, "/html/body/div[1]/div/div/div[2]/form/div[2]/button").click()

# 리다이렉트 대기
time.sleep(1)  # 페이지 로드 대기

# 특정 페이지로 이동 후 데이터 추출
driver.get("https://klas.kw.ac.kr/std/cps/inqire/AtnlcScreStdPage.do")

time.sleep(1)

# AType 클래스의 모든 테이블을 찾기
tables = driver.find_elements(By.CSS_SELECTOR, ".tablelistbox .AType")

# 결과를 저장할 리스트
results = []
result = []

for table in tables:
    print(table)

# 각 AType 테이블에 대해 반복
for table in tables:
    rows = table.find_elements(By.TAG_NAME, 'tr')  # 각 테이블의 모든 tr 요소 추출

    # 각 tr에 대해 5번째 td 값 확인
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, 'td')
        if len(cells) > 5:  # td가 6개 이상일 경우
            grade_cell = cells[5]
            if grade_cell.text in ["A+", "A0", "B+", "B0", "C+", "C0", "D+", "D0", "F", "P"]:
                lecture_number = cells[0].text
                lecture_name = cells[1].text
                results.append(lecture_number)
                result.append(lecture_name)

print(result)

# 결과 출력
print(results)

# 브라우저 종료
driver.quit()
