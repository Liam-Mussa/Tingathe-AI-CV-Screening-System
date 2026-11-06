// Sample data. Replace with calls to the FastAPI backend (see backend/main.py).
export const ADMIN_NAV = [['/admin','Dashboard','grid',true],['/admin/vacancies','Vacancies','briefcase'],['/admin/applications','Applications','files'],['/admin/users','Users','users'],['/admin/categories','Categories','tag'],['/admin/reports','Reports','chart'],['/admin/audit','Audit log','shield'],['/admin/settings','Settings','gear']]
export const vacancies = [
 {id:1,title:'Mathematics Teacher',cat:'Teaching',type:'Full time',status:'Open',closes:'14 Nov 2026',applicants:24,img:'maths',summary:'Teach Mathematics to Forms 1–4 and support the department.'},
 {id:2,title:'Physical Science Teacher',cat:'Teaching',type:'Full time',status:'Open',closes:'21 Nov 2026',applicants:11,img:'science',summary:'Lead practical science lessons and laboratory safety.'},
 {id:3,title:'School Accountant',cat:'Non-teaching',type:'Full time',status:'Open',closes:'28 Nov 2026',applicants:6,img:'accounts',summary:'Manage school accounts, fees records and reporting.'},
 {id:4,title:'School Librarian',cat:'Non-teaching',type:'Part time',status:'Draft',closes:'—',applicants:0,img:'library',summary:'Run the library and promote reading across the school.'},
 {id:5,title:'English Teacher',cat:'Teaching',type:'Full time',status:'Closed',closes:'30 Sep 2026',applicants:19,img:'english',summary:'Teach English language and literature to Forms 1–4.'}]
export const applicants = [
 {id:1,name:'Chikondi Banda',score:86,ext:'Complete',decision:'Shortlisted'},{id:2,name:'Tiyamike Phiri',score:79,ext:'Complete',decision:'Under review'},
 {id:3,name:'Mercy Chirwa',score:71,ext:'Review',decision:'Under review'},{id:4,name:'Limbani Mwale',score:58,ext:'Complete',decision:'Undecided'},{id:5,name:'Esther Nkhoma',score:null,ext:'Review',decision:'Manual check'}]
export const criteria = [['Degree in Mathematics Education',30],['Teaching registration',15],['Classroom experience (3+ years)',25],['Curriculum planning, assessment',20],['ICT in teaching',10]]
// Screening criteria per vacancy, so each vacancy screens against its own requirements.
export const criteriaByVacancy = {
  1:[['Degree in Mathematics Education',30],['Teaching registration',15],['Classroom experience (3+ years)',25],['Curriculum planning, assessment',20],['ICT in teaching',10]],
  2:[['Degree in Science Education',30],['Teaching registration',15],['Laboratory and practical experience',25],['Safety procedures and risk assessment',20],['ICT in teaching',10]],
  3:[['Diploma or degree in Accounting',35],['ACCA or professional qualification',15],['School fees and ledger experience',25],['Excel and accounting software',15],['Payroll and statutory reporting',10]],
  4:[['Diploma in Library Science',35],['Experience running a school library',25],['Reading promotion programmes',20],['Cataloguing and ICT systems',20]],
  5:[['Degree in English Education',30],['Teaching registration',15],['Literature and language teaching',25],['Curriculum planning and assessment',20],['ICT in teaching',10]]}
export const criteriaFor = id => criteriaByVacancy[id] || criteria
export const compare = [[30,30,24],[15,15,15],[18,20,12],[14,10,12],[9,4,8]]
export const users = [['William Mussa','william@example.com','Director','Active'],['Chikondi Banda','chikondi@example.com','Applicant','Active'],['Tiyamike Phiri','tiyamike@example.com','Applicant','Active'],['Esther Nkhoma','esther@example.com','Applicant','Disabled']]
export const pipeline = [['Submitted',30,100],['Processing',4,14],['Screened',22,73],['Needs review',3,10],['Decided',5,17]]
export const audit = [['Director','Recorded decision: shortlist','Application #1'],['System','Screening run completed','Mathematics Teacher'],['System','OCR used, low confidence','Degree_certificate.pdf'],['Director','Published vacancy','School Accountant']]
// Status labels for the applicant-facing tracker.
export const APP_STATUS = ['Received', 'Processing', 'Under review', 'Decision']
export const DEMO_APPLICANT = { name: 'Chikondi Banda', email: 'chikondi@example.com', phone: '+265 991 234 567', district: 'Lilongwe', role: 'applicant' }
