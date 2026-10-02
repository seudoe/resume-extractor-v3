export interface Address {
  city?: string;
  state?: string | null;
  country?: string;
  postal_code?: string | null;
}

export interface Affiliation {
  organization?: string;
  role?: string;
  type?: string;
  impact?: string[];
  period?: DateRange;
}

export interface Award {
  name?: string;
  issuingBody?: string;
  date?: string;
  justification?: string;
}

export interface Certification {
  name?: string;
  issuer?: string;
  skillsEarned?: string[];
  type?: string;
  date?: string;
}

export interface DateRange {
  start?: string;
  end?: string | null;
  isCurrent?: boolean;
}

export interface EducationField {
  type?: string;
  course?: string;
}

export interface ExtraLink {
  name?: string;
  link?: string;
}

export interface Interest {
  activity?: string;
  description?: string;
  commitmentMetric?: string | null;
}

export interface Language {
  lang?: string;
  proficiency?: string;
  score?: string | null;
}

export interface Project {
  title?: string;
  role?: string;
  links?: ProjectLinks;
  techStack?: string[];
  problemStatement?: string | null;
  metrics?: string[];
  technicalChallenges?: string[];
  description?: string[];
  architecture?: string;
}

export interface ProjectLinks {
  repo?: string;
  live?: string | null;
  demo?: string | null;
}

export interface Publication {
  title?: string;
  platform?: string;
  type?: "paper" | "article" | "talk";
  link?: string;
  keywords?: string[];
  date?: string;
}

export interface ResumeEducation {
  institution?: string;
  field?: EducationField;
  period?: DateRange;
  output?: string;
}

export interface ResumeMetaDetails {
  name?: string;
  phone_no?: string;
  gender?: "Male" | "Female" | "Other" | "Prefer Not to Say" | null;
  email?: string;
  github_profile?: string | null;
  linkedin?: string | null;
  address?: Address;
  extra_links?: ExtraLink[];
}

export interface Skill {
  field?: string;
  yearsOfExperience?: number;
  lastUsed?: string;
  tools?: SkillTool[];
}

export interface SkillTool {
  name?: string;
  score?: number | null;
}

export interface WorkHistory {
  title?: string;
  company?: string;
  location?: string;
  type?: "job" | "internship" | "volunteer" | "co-op";
  period?: DateRange;
  responsibilities?: string[];
  achievements?: string[];
}

export interface ParsedResumeData {
  summary?: string;
  workHistory?: WorkHistory[];
  education?: ResumeEducation[];
  skills?: Skill[];
  projects?: Project[];
  certifications?: Certification[];
  languages?: Language[];
  publications?: Publication[];
  affiliations?: Affiliation[];
  awards?: Award[];
  interests?: Interest[];
  metaDetails?: ResumeMetaDetails;
  bert_vector?: number[] | null;
  tfidf__vector?: number[] | null;
}
