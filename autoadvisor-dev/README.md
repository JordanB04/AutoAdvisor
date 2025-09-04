Read the User Guide for installation instructions

Store ALL python files in the same file directory.
To run program, run project.py.

This program requires the following resources to run:
  - Edge Webdriver: https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
  - Selenium 4: https://www.selenium.dev/documentation/webdriver/getting_started/install_library/
  - Pandas
  - Openpyxl

'project' will prompt the user for their credentials, use them to log into VSU's Banner, crawl through the webpage to the student's transcript and scrape it. After it scrapes the transcript, it then prints out two files, one that stores all the courses and another that stores all the semesters. 'project' passes those files to 'preprocess', which then structures and concentrates the two files into a course matrix. 'preprocess' passes that course matrix onto 'advise' which analyzes that matrix to generate an advisory report.
