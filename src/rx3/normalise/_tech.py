"""Curated technology table: group -> entries "Canonical|alias|alias". Aliases are matched case-insensitively
on word boundaries; `CASE_SENSITIVE` ones (single letters, common words) only inside explicit skill lists.
The group names are the `field` buckets used for ungrouped skills (the taxonomy file of PROMPT.md Stage 11)."""

TECH: dict[str, list[str]] = {
    "Programming Languages": [
        "Python|py", "JavaScript|js|java script|ecmascript", "TypeScript|ts", "Java", "C++|cpp", "C#|csharp|c sharp", "C",
        "Go|golang", "Rust", "Kotlin", "Swift", "Ruby", "PHP", "Scala", "R", "MATLAB", "Perl", "Dart", "Bash|shell scripting|shell",
        "SQL", "HTML|html5", "CSS|css3", "Objective-C", "Haskell", "Lua", "Julia", "Solidity", "VHDL", "Verilog", "Assembly",
        "PowerShell", "Groovy", "Elixir", "Clojure", "COBOL", "Fortran", "Visual Basic|vb.net",
    ],
    "Web Technologies": [
        "React|react.js|reactjs", "Next.js|nextjs|next js", "Angular|angularjs|angular.js", "Vue.js|vue|vuejs", "Svelte",
        "Node.js|nodejs|node js|node", "Express.js|express|expressjs", "Django", "Flask", "FastAPI", "Spring Boot|springboot",
        "Spring", "Laravel", "Ruby on Rails|rails", "ASP.NET|asp.net core", ".NET|dotnet|.net core", "Redux", "jQuery",
        "Tailwind CSS|tailwind|tailwindcss", "Bootstrap", "Sass|scss", "Material-UI|material ui|mui", "Vite", "Webpack",
        "GraphQL", "REST|restful|rest api|rest apis|restful apis", "WebSocket|websockets", "Socket.io|socket.io", "Flutter",
        "React Native", "Jest", "Cypress", "Selenium", "JWT", "OAuth|oauth2", "Passport.js|passport",
    ],
    "Databases": [
        "MySQL", "PostgreSQL|postgres|postgresql", "MongoDB|mongo|mongo db", "Redis", "SQLite", "Oracle|oracle db", "SQL Server|mssql|ms sql",
        "Cassandra", "DynamoDB", "Firebase", "Firestore", "Elasticsearch|elastic search", "MariaDB", "Neo4j", "Supabase",
        "Snowflake", "BigQuery", "Mongoose", "Prisma", "SQLAlchemy", "Hive", "HBase",
    ],
    "Cloud & DevOps": [
        "AWS|amazon web services", "Azure|microsoft azure", "GCP|google cloud|google cloud platform", "Docker", "Kubernetes|k8s",
        "Terraform", "Ansible", "Jenkins", "GitHub Actions", "GitLab CI", "CI/CD|ci cd", "Linux", "Nginx", "Heroku", "Netlify",
        "Vercel", "Render", "Back4app", "Prometheus", "Grafana", "Kafka|apache kafka", "RabbitMQ", "Lambda|aws lambda",
        "EC2", "S3", "Helm", "Istio", "Vagrant", "Unix",
    ],
    "Data Science & ML": [
        "Machine Learning|ml", "Deep Learning|dl", "NLP|natural language processing", "Computer Vision|cv",
        "TensorFlow", "PyTorch|torch", "Keras", "scikit-learn|sklearn|scikit learn", "Pandas", "NumPy", "SciPy", "Matplotlib",
        "Seaborn", "Plotly", "OpenCV", "Hugging Face|huggingface", "Transformers", "LangChain", "XGBoost", "LightGBM",
        "Spark|apache spark|pyspark", "Hadoop", "Airflow|apache airflow", "Power BI|powerbi", "Tableau", "Excel|ms excel|microsoft excel",
        "Jupyter", "Statistics", "Data Analysis", "Data Visualization", "A/B Testing", "ETL", "RAG", "LLM|llms",
    ],
    "Tools & Platforms": [
        "Git", "GitHub", "GitLab", "Bitbucket", "Jira", "Confluence", "Postman", "VS Code|vscode|visual studio code",
        "IntelliJ", "Eclipse", "Figma", "Canva", "Photoshop", "Illustrator", "Slack", "Trello", "Notion", "Make", "CMake",
        "Maven", "Gradle", "npm", "Yarn", "pip", "Xcode", "Android Studio", "Unity", "Arduino", "Raspberry Pi", "Linux",
        "Salesforce", "SAP", "QuickBooks", "AutoCAD", "SolidWorks", "Microsoft Office|ms office", "Word|ms word",
        "PowerPoint|ms powerpoint", "Outlook",
    ],
    "Core Concepts": [
        "Data Structures|dsa|data structures and algorithms|data structures & algorithms", "Algorithms", "OOP|object oriented programming|object-oriented programming",
        "Operating Systems|os", "DBMS", "Computer Networks|networking", "System Design", "Microservices", "Agile", "Scrum",
        "Design Patterns", "Competitive Programming", "Cybersecurity", "Blockchain", "IoT",
    ],
}
CASE_SENSITIVE = {"C", "R", "Go", "Make", "Render", "Spring", "Express", "Word", "Oracle", "Node", "Vue", "S3", "EC2", "OS", "CV", "DL", "ML", "ETL", "RAG", "JWT", "REST", "Hive", "Lambda", "Transformers", "Statistics"}
# aliases too ambiguous for free-text discovery (only used to canonicalise items already in a skill list / tech line)
LIST_ONLY = {"C", "R", "Go", "Make", "Render", "Spring", "Express", "Word", "Oracle", "Node", "Vue", "Hive", "Lambda", "Transformers",
             "Statistics", "Shell", "OS", "CV", "DL", "Unix", "Jest", "Rails", "Swift", "Dart", "Scala", "Julia", "Mongoose", "Prisma"}
