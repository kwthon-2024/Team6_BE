from selenium import webdriver
from selenium.webdriver.common.by import By
import time



def get_klas(klas_id:str, klas_pw:str):
    # 웹 드라이버 설정
    driver = webdriver.Chrome()  # Chrome 드라이버 경로 설정 필요

    # 로그인 페이지로 이동
    driver.get("https://klas.kw.ac.kr/usr/cmn/login/LoginForm.do")

    time.sleep(2)

    # 로그인 정보 입력
    driver.find_element(By.ID, "loginId").send_keys(klas_id)
    driver.find_element(By.ID, "loginPwd").send_keys(klas_pw)

    time.sleep(1)

    # 로그인 버튼 클릭
    driver.find_element(By.XPATH, "/html/body/div[1]/div/div/div[2]/form/div[2]/button").click()

    # 리다이렉트 대기
    time.sleep(2)  # 페이지 로드 대기

    # 특정 페이지로 이동
    driver.get("https://klas.kw.ac.kr/std/cps/inqire/AtnlcScreStdPage.do")
    time.sleep(2)

    # 사용자 이름 가져오기
    user_name_element = driver.find_element(By.XPATH, "/html/body/header/div[1]/div/div[2]/a[1]")
    user_name_text = user_name_element.text

    klas_user_name = user_name_text.split('(')[0].strip()  
    klas_user_year = user_name_text.split('(')[1][2:4] 

    # 결과 출력
    print("klas name:", klas_user_name)
    print("klas user year:", klas_user_year)

    # AType 클래스의 모든 테이블을 찾기
    tables = driver.find_elements(By.CSS_SELECTOR, ".tablelistbox .AType")

    # 결과를 저장할 딕셔너리 초기화
    all_results = {}

    # 각 AType 테이블에 대해 반복
    for table in tables:
        # thead 내의 tr 내의 th 내의 텍스트를 변수에 저장
        headers = table.find_elements(By.CSS_SELECTOR, "thead tr th")
        header_texts = [header.text for header in headers]
        
        # tbody 내의 tr 내의 td들 전체 가져오기
        rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
        table_data = []

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            cell_texts = [cell.text for cell in cells]
            table_data.append(cell_texts)

        # header_texts[0]을 키로 하고 table_data를 값으로 추가
        if header_texts:  # header_texts가 비어있지 않을 경우에만 추가
            all_results[header_texts[0]] = table_data

    # 최종 결과 출력
    print(all_results)

    # 드라이버 종료
    driver.quit()
    return klas_user_name, klas_user_year, all_results


# print("Results:", results)


# # 결과를 저장할 리스트
# results = []
# result = []

# for table in tables:
#     print(table)

# # 각 AType 테이블에 대해 반복
# for table in tables:
#     rows = table.find_elements(By.TAG_NAME, 'tr')  # 각 테이블의 모든 tr 요소 추출

#     # 각 tr에 대해 5번째 td 값 확인
#     for row in rows:
#         cells = row.find_elements(By.TAG_NAME, 'td')
#         if len(cells) > 5:  # td가 6개 이상일 경우
#             grade_cell = cells[5]
#             if grade_cell.text in ["A+", "A0", "B+", "B0", "C+", "C0", "D+", "D0", "F", "P"]:
#                 lecture_number = cells[0].text
#                 lecture_name = cells[1].text
#                 results.append(lecture_number)
#                 result.append(lecture_name)

# print(result)

# # 결과 출력
# print(results)

# # 브라우저 종료
# driver.quit()
