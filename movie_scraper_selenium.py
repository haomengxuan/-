import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
from datetime import datetime
import os

class MaoyanSeleniumScraper:
    def __init__(self):
        self.base_url = "https://www.maoyan.com/films?yearId=19&showType=3&sortId=1"
        self.movies_data = []
        self.setup_driver()
        # 创建临时文件名
        self.temp_filename = f"maoyan_movies_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
    def setup_driver(self):
        """设置Selenium WebDriver"""
        chrome_options = Options()
        # 添加一些选项来模拟真实浏览器
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # 如果需要无头模式（不显示浏览器窗口），取消下面这行的注释
        # chrome_options.add_argument("--headless")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        # 设置页面加载超时
        self.driver.set_page_load_timeout(30)
        # 设置窗口大小
        self.driver.set_window_size(1920, 1080)
        
        # 执行JavaScript来修改navigator.webdriver属性，避免被检测
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def save_temp_data(self):
        """保存临时数据到CSV文件"""
        if self.movies_data:
            df = pd.DataFrame(self.movies_data)
            df.to_csv(self.temp_filename, index=False, encoding='utf-8-sig')
            print(f"已保存临时数据到 {self.temp_filename}")

    def get_page(self, page=1):
        """获取指定页码的电影列表页面"""
        url = f"{self.base_url}&offset={(page-1)*30}"
        try:
            print(f"正在访问第 {page} 页: {url}")
            self.driver.get(url)
            
            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".movie-item"))
            )
            
            # 随机滚动页面
            self.random_scroll()
            
            return True
        except TimeoutException:
            print(f"页面加载超时: {url}")
            return False
        except Exception as e:
            print(f"访问页面时出错: {e}")
            return False

    def random_scroll(self):
        """随机滚动页面，模拟人类行为"""
        try:
            # 获取页面高度
            page_height = self.driver.execute_script("return document.body.scrollHeight")
            # 随机滚动几次
            for _ in range(random.randint(3, 7)):
                # 随机滚动到页面中间位置
                scroll_position = random.randint(300, page_height - 300)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                # 随机暂停
                time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            print(f"滚动页面时出错: {e}")

    def get_movie_detail(self, movie_url, rating="暂无评分"):
        """获取电影详情页面的信息"""
        try:
            # 打开新标签页访问电影详情
            self.driver.execute_script(f"window.open('{movie_url}', '_blank');")
            # 切换到新标签页
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".movie-brief-container"))
            )
            
            # 随机滚动页面
            self.random_scroll()
            
            # 提取电影标题
            title = "未知"
            try:
                title_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.name"))
                )
                title = title_element.text.strip()
            except:
                print("无法获取电影标题")
            
            # 提取导演
            director = "未知"
            try:
                # 等待导演信息加载
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".celebrity-group"))
                )
                director_elements = self.driver.find_elements(By.CSS_SELECTOR, ".celebrity-group:first-child .info .name")
                if director_elements:
                    director = director_elements[0].text.strip()
            except:
                print("无法获取导演信息")
                
            # 提取演员
            actors = "未知"
            try:
                actor_elements = self.driver.find_elements(By.CSS_SELECTOR, ".celebrity-group:nth-child(2) .info .name")
                if actor_elements:
                    actors = ", ".join([actor.text.strip() for actor in actor_elements[:3]])
            except:
                print("无法获取演员信息")
                
            # 提取类型和上映日期
            genre = "未知"
            release_date = "未知"
            try:
                # 等待电影信息加载
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".movie-brief-container"))
                )
                # 获取所有基本信息
                info_elements = self.driver.find_elements(By.CSS_SELECTOR, ".movie-brief-container ul li")
                if info_elements:
                    # 第一个元素通常是类型
                    genre = info_elements[0].text.strip()
                    # 最后一个元素通常是上映日期
                    release_date = info_elements[-1].text.strip()
            except:
                print("无法获取类型和上映日期信息")

            # 获取票房信息（直接从详情页获取）
            first_week_box = "未知"
            total_box = "未知"
            try:
                # 等待票房信息加载并滚动到底部
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                )
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # 首先尝试使用XPath直接定位包含票房数据的元素
                try:
                    # 查找包含"票房详情"的元素
                    detail_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '票房详情')]")
                    if detail_elements:
                        # 找到票房详情元素的父节点
                        parent = self.driver.execute_script("return arguments[0].parentNode;", detail_elements[0])
                        if parent:
                            # 获取父节点中所有的值和标签
                            numbers = parent.find_elements(By.CSS_SELECTOR, "p")
                            labels = parent.find_elements(By.CSS_SELECTOR, ".mbox-name")
                            
                            # 遍历所有标签和对应的值
                            for i in range(min(len(numbers), len(labels))):
                                label_text = labels[i].text.strip()
                                value_text = numbers[i].text.strip()
                                
                                print(f"找到标签: '{label_text}', 值: '{value_text}'")
                                
                                if "首周票房" in label_text:
                                    first_week_box = value_text
                                    print(f"首周票房: {first_week_box}")
                                elif "累计票房" in label_text:
                                    total_box = value_text
                                    print(f"累计票房: {total_box}")
                except Exception as e:
                    print(f"通过票房详情元素获取票房数据失败: {e}")
                
                # 如果上面的方法失败，使用另一种方法
                if first_week_box == "未知" or total_box == "未知":
                    # 尝试直接获取.mbox-name元素及其对应的数值
                    box_names = self.driver.find_elements(By.CSS_SELECTOR, ".mbox-name")
                    
                    # 遍历所有.mbox-name元素
                    for i, box_name in enumerate(box_names):
                        try:
                            name_text = box_name.text.strip()
                            # 找到对应的数值元素（通常是前一个兄弟元素）
                            if "首周票房" in name_text:
                                # 尝试获取兄弟元素中的数值
                                value_element = box_names[i-1] if i > 0 else None
                                if value_element:
                                    value_text = value_element.text.strip()
                                    # 检查是否是数字
                                    if value_text and value_text != name_text:
                                        first_week_box = value_text
                                        print(f"直接从元素获取首周票房: {first_week_box}")
                            elif "累计票房" in name_text:
                                # 尝试获取兄弟元素中的数值
                                value_element = box_names[i-1] if i > 0 else None
                                if value_element:
                                    value_text = value_element.text.strip()
                                    # 检查是否是数字
                                    if value_text and value_text != name_text:
                                        total_box = value_text
                                        print(f"直接从元素获取累计票房: {total_box}")
                        except Exception as e:
                            print(f"处理票房名称元素时出错: {e}")
                
                # 如果上述方法都失败，使用原始XPath方法提取父元素文本
                if first_week_box == "未知" or total_box == "未知":
                    box_office_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '票房')]")
                    
                    for element in box_office_elements:
                        try:
                            # 获取元素的文本和父元素文本
                            text = element.text.strip()
                            parent = self.driver.execute_script("return arguments[0].parentNode;", element)
                            parent_text = parent.text if parent else ""
                            
                            # 首周票房处理
                            if "首周票房" in text or "首周票房" in parent_text:
                                # 在父元素文本中查找数字
                                match = re.search(r'(\d+)\s*首周票房', parent_text)
                                if match:
                                    first_week_box = match.group(1)
                                    print(f"从父元素文本中提取首周票房: {first_week_box}")
                            
                            # 累计票房处理
                            if "累计票房" in text or "累计票房" in parent_text:
                                # 在父元素文本中查找数字
                                match = re.search(r'(\d+)\s*累计票房', parent_text)
                                if match:
                                    total_box = match.group(1)
                                    print(f"从父元素文本中提取累计票房: {total_box}")
                        except Exception as e:
                            print(f"处理XPath元素时出错: {e}")
            except Exception as e:
                print(f"获取票房信息时出错: {e}")

            # 关闭当前标签页
            self.driver.close()
            # 切回主标签页
            self.driver.switch_to.window(self.driver.window_handles[0])
            
            movie_data = {
                'Title': title,
                'Rating': rating,
                'Director': director,
                'Actors': actors,
                'Genre': genre,
                'ReleaseDate': release_date,
                'FirstWeekBox': first_week_box,
                'TotalBox': total_box
            }
            
            # 每当成功解析一部电影就保存一次临时数据
            self.movies_data.append(movie_data)
            self.save_temp_data()
            print(f"成功解析电影: {title} ({release_date})")
            
            return movie_data
            
        except Exception as e:
            print(f"获取电影详情时出错: {e}")
            # 确保切回主标签页
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
            return None
            
    def scrape_movies(self):
        """爬取所有电影数据"""
        page = 1
        max_pages = 10  # 最多爬取10页
        
        while page <= max_pages:
            if not self.get_page(page):
                print(f"无法获取第 {page} 页，停止爬取")
                break
                
            # 获取当前页面的所有电影元素
            try:
                # 等待电影元素加载
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".movie-item"))
                )
                movie_elements = self.driver.find_elements(By.CSS_SELECTOR, ".movie-item")
                
                if not movie_elements:
                    print(f"第 {page} 页没有找到电影元素，停止爬取")
                    break
                    
                print(f"第 {page} 页找到 {len(movie_elements)} 部电影")
                
                # 解析每部电影
                for i, movie_element in enumerate(movie_elements, 1):
                    try:
                        # 获取电影链接
                        link_element = movie_element.find_element(By.CSS_SELECTOR, "a")
                        movie_url = link_element.get_attribute("href")
                        
                        # 获取评分信息
                        rating = "暂无评分"
                        try:
                            # 使用相对XPath获取评分
                            rating_xpath = f"/html/body/div[4]/div/div[2]/div[2]/dl/dd[{i}]/div[3]"
                            rating_element = self.driver.find_element(By.XPATH, rating_xpath)
                            if rating_element:
                                rating = rating_element.text.strip()
                                if not rating:  # 如果评分为空，尝试获取想看人数
                                    wish_element = rating_element.find_element(By.CSS_SELECTOR, ".wish")
                                    if wish_element:
                                        rating = f"想看人数: {wish_element.text.strip()}"
                        except NoSuchElementException:
                            print(f"无法获取电影评分")
                        
                        if movie_url:
                            # 确保链接是完整的URL
                            if not movie_url.startswith("http"):
                                movie_url = f"https://www.maoyan.com{movie_url}"
                            
                            # 修改get_movie_detail方法调用，传入已获取的评分
                            self.get_movie_detail(movie_url, rating)
                            
                            # 每部电影处理完后添加随机延迟
                            time.sleep(random.uniform(1, 3))
                    except Exception as e:
                        print(f"处理电影元素时出错: {e}")
                        continue
                
                # 页面处理完后添加随机延迟
                time.sleep(random.uniform(2, 4))
                page += 1
                
            except Exception as e:
                print(f"处理第 {page} 页时出错: {e}")
                break
            
    def save_to_csv(self):
        """保存电影数据到CSV文件"""
        if self.movies_data:
            df = pd.DataFrame(self.movies_data)
            filename = f"maoyan_movies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"成功保存 {len(self.movies_data)} 部电影到 {filename}")
            
            # 删除临时文件
            if os.path.exists(self.temp_filename):
                os.remove(self.temp_filename)
                print(f"已删除临时文件 {self.temp_filename}")
        else:
            print("没有电影数据可保存")
            
    def close(self):
        """关闭浏览器"""
        self.driver.quit()
        
def main():
    scraper = MaoyanSeleniumScraper()
    try:
        scraper.scrape_movies()
        scraper.save_to_csv()
    finally:
        scraper.close()
        
if __name__ == "__main__":
    main() 