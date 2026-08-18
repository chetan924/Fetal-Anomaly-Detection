import { useMemo, useState } from 'react';

import {
  AlertCircle,
  BarChart3,
  Bell,
  Brain,
  CheckCircle2,
  ChevronDown,
  FileText,
  HelpCircle,
  Image as ImageIcon,
  LockKeyhole,
  Search,
  Settings,
  ShieldCheck,
  Stethoscope,
  Upload,
  Users,
  XCircle,
  Zap,
} from 'lucide-react';

import Card from '../components/ui/Card';


// ============================================================
// HELP CONTENT
// ============================================================

const HELP_SECTIONS = [
  {
    id: 'getting-started',
    category: 'Getting Started',
    title: 'Getting Started with FetalAI',
    icon: Zap,
    description:
      'Learn the basic workflow for using the FetalAI clinical screening workspace.',
    content: [
      {
        question: 'What is FetalAI?',
        answer:
          'FetalAI is an AI-assisted fetal ultrasound screening workspace. It allows authorized users to manage patients, upload ultrasound images, run AI-assisted analysis, review model confidence, inspect statistical screening results, view Grad-CAM explainability outputs, and generate reports.',
      },
      {
        question: 'What is the recommended workflow?',
        answer:
          'The recommended workflow is: create or select a patient, start a new scan, upload a supported ultrasound image, run AI analysis, review the fetal-plane prediction, review any available brain-plane analysis and statistical screening, inspect Grad-CAM when available, and then open the full report.',
      },
      {
        question: 'Where should I start?',
        answer:
          'Start from the Dashboard to see the current workspace summary. Use Patients to manage patient records, New Scan to perform a new AI-assisted analysis, Scan History to review previous scans, and Reports to inspect detailed results.',
      },
    ],
  },

  {
    id: 'patients',
    category: 'Patients',
    title: 'Patient Management',
    icon: Users,
    description:
      'Manage patient records and review patient-specific scan history.',
    content: [
      {
        question: 'How do I create a patient?',
        answer:
          'Open the Patients section and use the available patient creation action. Enter the required patient information and save the record. The patient can then be selected when creating a new scan.',
      },
      {
        question: 'How do I view a patient’s scans?',
        answer:
          'Select a patient from the Patients page. The patient view provides access to that patient’s scan history and available AI analysis information.',
      },
      {
        question: 'Can I open a report for a specific scan?',
        answer:
          'Yes. From patient scan history or Scan History, select the required scan and use Open Full Report. The application opens the report for that exact scan rather than automatically selecting another scan.',
      },
    ],
  },

  {
    id: 'new-scan',
    category: 'New Scan',
    title: 'Creating a New Scan',
    icon: Upload,
    description:
      'Step-by-step instructions for uploading and analyzing an ultrasound image.',
    content: [
      {
        question: 'How do I create a new scan?',
        answer:
          'Open New Scan, select the appropriate patient, upload the ultrasound image, review the selected file, and start the analysis. After processing finishes, review the returned AI results before opening the full report.',
      },
      {
        question: 'Which image formats are supported?',
        answer:
          'The current backend accepts PNG and JPEG image files. The configured maximum upload size is 10 MB.',
      },
      {
        question: 'What happens after I upload an image?',
        answer:
          'The backend validates the patient, file type, file size, and image content. The image is then passed to the fetal-plane prediction pipeline. When the predicted plane is appropriate and confidence is sufficient, additional plane-specific analysis can be performed.',
      },
      {
        question: 'What happens if the upload fails?',
        answer:
          'Check that a patient is selected, the image is a valid PNG or JPEG file, and the file is within the configured size limit. If the backend or AI service is unavailable, retry after checking the API status.',
      },
    ],
  },

  {
    id: 'ai-analysis',
    category: 'AI Analysis',
    title: 'Understanding AI Analysis',
    icon: Brain,
    description:
      'Understand fetal-plane classification, confidence and additional analysis.',
    content: [
      {
        question: 'What is fetal-plane classification?',
        answer:
          'The fetal-plane classifier predicts which ultrasound plane is represented by the uploaded image. The result includes a predicted class, confidence value, and class probabilities.',
      },
      {
        question: 'What does confidence mean?',
        answer:
          'Confidence represents the model probability associated with the predicted class. A high confidence value means the model assigned a high probability to that class. Confidence should be interpreted as a model output, not as clinical certainty.',
      },
      {
        question: 'What are the probability values?',
        answer:
          'The probabilities provide the model’s estimated probability for each supported class. They help show how strongly the model preferred the predicted class compared with the alternatives.',
      },
      {
        question: 'What if the model predicts Other?',
        answer:
          'Other indicates that the model did not classify the image as one of the supported primary fetal-plane categories. Review the image quality and clinical context before deciding whether another scan should be analyzed.',
      },
    ],
  },

  {
    id: 'brain-analysis',
    category: 'Brain Analysis',
    title: 'Brain-Plane Analysis',
    icon: Brain,
    description:
      'Understand the additional analysis performed for fetal-brain images.',
    content: [
      {
        question: 'When is brain analysis performed?',
        answer:
          'Brain-specific analysis is performed when the fetal-plane prediction identifies a fetal-brain image and the pipeline determines that the confidence is sufficient for plane-specific analysis.',
      },
      {
        question: 'What are the brain-plane categories?',
        answer:
          'The current pipeline can classify brain images into Trans-thalamic, Trans-ventricular, and Trans-cerebellum categories.',
      },
      {
        question: 'What does the brain confidence represent?',
        answer:
          'It is the model confidence associated with the predicted brain plane. As with other AI confidence values, it should be treated as model output and not as a standalone clinical conclusion.',
      },
    ],
  },

  {
    id: 'outlier',
    category: 'Statistical Screening',
    title: 'Statistical Outlier Screening',
    icon: BarChart3,
    description:
      'Understand the experimental statistical screening result.',
    content: [
      {
        question: 'What is outlier analysis?',
        answer:
          'The outlier analysis compares the analyzed image with the statistical distribution represented by the reference data used by the pipeline. It produces an anomaly score and compares that score with a configured threshold.',
      },
      {
        question: 'What does In-distribution mean?',
        answer:
          'In-distribution means the image falls within the statistical distribution represented by the reference dataset according to the configured screening method.',
      },
      {
        question: 'What does Review mean?',
        answer:
          'A review or outlier result means the image was flagged by the experimental statistical screening mechanism. It does not mean that a fetal anomaly has been diagnosed.',
      },
      {
        question: 'Is the outlier result a medical diagnosis?',
        answer:
          'No. The current application explicitly treats statistical outlier screening as experimental. It is not a clinically validated fetal anomaly diagnosis and must be reviewed by a qualified healthcare professional.',
      },
    ],
  },

  {
    id: 'gradcam',
    category: 'Explainability',
    title: 'Grad-CAM Explainability',
    icon: ImageIcon,
    description:
      'Understand heatmaps and overlays generated by the AI pipeline.',
    content: [
      {
        question: 'What is Grad-CAM?',
        answer:
          'Grad-CAM is an explainability technique used to visualize regions of an image that contributed to a neural-network prediction. FetalAI can provide a heatmap and an overlay when explainability output is available.',
      },
      {
        question: 'What is the heatmap?',
        answer:
          'The heatmap is a visualization of model attention or activation associated with the selected target class.',
      },
      {
        question: 'What is the overlay?',
        answer:
          'The overlay combines the original ultrasound image with the Grad-CAM visualization so that the highlighted regions can be viewed in the context of the source image.',
      },
      {
        question: 'Does Grad-CAM prove that the highlighted area is abnormal?',
        answer:
          'No. Grad-CAM shows model-related attention or activation. It should not be interpreted as proof of an abnormality or as a clinical diagnosis.',
      },
    ],
  },

  {
    id: 'reports',
    category: 'Reports',
    title: 'Reports & PDF',
    icon: FileText,
    description:
      'Review detailed scan results and generate reports.',
    content: [
      {
        question: 'How do I open a full report?',
        answer:
          'Use Open Full Report from a scan in Scan History, Patient scan history, or after completing a New Scan. The report is opened using the exact scan ID.',
      },
      {
        question: 'What information is shown in a report?',
        answer:
          'A detailed report can include patient information, scan information, fetal-plane prediction, confidence, class probabilities, brain-plane analysis when available, statistical screening, Grad-CAM explainability information, and clinical disclaimers.',
      },
      {
        question: 'Can I generate a PDF?',
        answer:
          'Yes. The Reports workflow provides PDF/report generation functionality when the required report data is available.',
      },
      {
        question: 'Why is the clinical disclaimer included?',
        answer:
          'The disclaimer clearly communicates that AI-assisted screening and experimental statistical outputs are intended for clinical review and should not be treated as standalone clinically validated diagnoses.',
      },
    ],
  },

  {
    id: 'notifications',
    category: 'Notifications',
    title: 'Notifications',
    icon: Bell,
    description:
      'Understand scan, AI processing and system notifications.',
    content: [
      {
        question: 'What notifications can I receive?',
        answer:
          'Notifications can describe successful scan analysis, statistical screening alerts, analysis failures, and important system events.',
      },
      {
        question: 'How do I mark notifications as read?',
        answer:
          'Open Notifications and use Mark as read for an individual notification or Mark all as read to clear all unread indicators.',
      },
      {
        question: 'Can a notification open a report?',
        answer:
          'Notifications associated with a scan can provide an Open report action. This opens the report for the related scan ID.',
      },
    ],
  },

  {
    id: 'settings',
    category: 'Settings',
    title: 'Settings & Preferences',
    icon: Settings,
    description:
      'Manage profile, password, notifications and report preferences.',
    content: [
      {
        question: 'How do I change my password?',
        answer:
          'Open Settings → Security. Enter your current password, choose a new password, confirm it, and select Change password. The current implementation requires at least 8 characters for the new password.',
      },
      {
        question: 'Where are notification preferences managed?',
        answer:
          'Open Settings → Notifications. You can control scan-completion, statistical-screening, analysis-failure and system notification preferences.',
      },
      {
        question: 'Where are report preferences managed?',
        answer:
          'Open Settings → Reports & Clinical Workflow. You can configure whether confidence, methodology and the clinical disclaimer are included in generated reports.',
      },
      {
        question: 'Where are settings stored?',
        answer:
          'The current settings page stores workspace preferences locally on the device using browser local storage. Authentication and password changes are handled through the backend.',
      },
    ],
  },

  {
    id: 'security',
    category: 'Security',
    title: 'Account & Security',
    icon: LockKeyhole,
    description:
      'Basic guidance for protecting your FetalAI account.',
    content: [
      {
        question: 'How should I protect my account?',
        answer:
          'Use a strong, unique password and do not share your authentication credentials. Change your password if you believe your credentials may have been exposed.',
      },
      {
        question: 'Is my current password stored in Settings?',
        answer:
          'No. The Settings page does not store the current password in browser preferences. Password changes are sent through the authenticated backend flow.',
      },
      {
        question: 'What should I do if authentication fails?',
        answer:
          'Verify that you are logged in, check whether the backend API is available, and sign in again if the access token has expired. If the issue continues, contact the system administrator.',
      },
    ],
  },

  {
    id: 'troubleshooting',
    category: 'Troubleshooting',
    title: 'Troubleshooting',
    icon: AlertCircle,
    description:
      'Common problems and practical steps to resolve them.',
    content: [
      {
        question: 'The Dashboard says the API is offline.',
        answer:
          'Check that the FetalAI backend is running and reachable. In the current development environment the backend health endpoint is available at /health on port 8000. Also verify that the frontend API base URL is configured correctly.',
      },
      {
        question: 'The scan analysis failed.',
        answer:
          'Confirm the patient exists, the uploaded image is a valid PNG or JPEG, and the file is not larger than the configured 10 MB limit. Then check the backend logs for the AI pipeline error.',
      },
      {
        question: 'Grad-CAM images are not loading.',
        answer:
          'Confirm that the backend successfully generated the explainability files and that the returned storage paths are reachable from the frontend. The backend exposes explainability files under its storage path.',
      },
      {
        question: 'The report opens for the wrong scan.',
        answer:
          'Use the Full Report action associated with the specific scan. The current workflow uses /reports?scan=<scan_id> so that the exact scan can be loaded from the backend.',
      },
      {
        question: 'The page looks outdated after a code change.',
        answer:
          'Run the frontend production build and refresh the browser. During development, also verify that the Vite development server is running the current source files.',
      },
    ],
  },

  {
    id: 'clinical',
    category: 'Clinical Safety',
    title: 'Clinical Use & Disclaimer',
    icon: Stethoscope,
    description:
      'Important information about interpreting FetalAI outputs.',
    content: [
      {
        question: 'Can FetalAI diagnose fetal anomalies?',
        answer:
          'No. FetalAI is an AI-assisted screening and analysis workspace. Its AI predictions, confidence values, Grad-CAM visualizations and experimental statistical screening outputs should not be treated as standalone clinically validated diagnoses.',
      },
      {
        question: 'Who should interpret the results?',
        answer:
          'Results should be reviewed and interpreted by an appropriately qualified healthcare professional together with the ultrasound image, clinical history and other relevant clinical information.',
      },
      {
        question: 'What should I do with a flagged result?',
        answer:
          'Treat a flagged statistical screening result as an indication for review rather than a diagnosis. Review the source image and the available AI outputs and follow the appropriate clinical workflow.',
      },
    ],
  },
];


// ============================================================
// COMPONENT
// ============================================================

export default function HelpPage() {

  const [
    search,
    setSearch,
  ] = useState('');

  const [
    activeSection,
    setActiveSection,
  ] = useState(
    HELP_SECTIONS[0].id
  );

  const [
    openQuestions,
    setOpenQuestions,
  ] = useState(
    new Set([
      HELP_SECTIONS[0]
        .content[0]
        .question,
    ])
  );


  // ==========================================================
  // FILTER
  // ==========================================================

  const filteredSections =
    useMemo(() => {

      const query =
        search
          .trim()
          .toLowerCase();

      if (!query) {
        return HELP_SECTIONS;
      }

      return HELP_SECTIONS
        .map((section) => {

          const sectionMatches =
            `${section.category} ${section.title} ${section.description}`
              .toLowerCase()
              .includes(query);

          const matchingContent =
            section.content.filter(
              (item) =>
                `${item.question} ${item.answer}`
                  .toLowerCase()
                  .includes(query)
            );

          if (
            sectionMatches ||
            matchingContent.length > 0
          ) {

            return {
              ...section,
              content:
                sectionMatches
                  ? section.content
                  : matchingContent,
            };

          }

          return null;

        })
        .filter(Boolean);

    }, [search]);


  // ==========================================================
  // TOGGLE QUESTION
  // ==========================================================

  const toggleQuestion = (
    question
  ) => {

    setOpenQuestions(
      (previous) => {

        const next =
          new Set(previous);

        if (
          next.has(question)
        ) {

          next.delete(question);

        } else {

          next.add(question);

        }

        return next;

      }
    );

  };


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <div className="space-y-6">

      {/* ====================================================
          HEADER
      ==================================================== */}

      <div>

        <div className="flex items-center gap-3">

          <div className="rounded-xl bg-teal-50 p-2.5">

            <HelpCircle
              size={22}
              className="text-teal-600"
            />

          </div>


          <div>

            <h1 className="text-2xl font-semibold text-slate-900">
              Help & Support
            </h1>


            <p className="mt-1 text-sm text-slate-500">
              Learn how to use FetalAI, understand AI-assisted
              screening results, and troubleshoot common issues.
            </p>

          </div>

        </div>

      </div>


      {/* ====================================================
          SEARCH
      ==================================================== */}

      <Card>

        <div className="relative">

          <Search
            size={18}
            className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
          />


          <input
            value={search}
            onChange={(event) =>
              setSearch(
                event.target.value
              )
            }
            placeholder="Search help topics, AI analysis, reports, Grad-CAM..."
            className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-11 pr-4 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
          />

        </div>


        {search && (

          <p className="mt-3 text-xs text-slate-500">

            {filteredSections.length ===
            0
              ? 'No help topics found.'
              : `${filteredSections.length} help section${
                  filteredSections.length > 1
                    ? 's'
                    : ''
                } found.`}

          </p>

        )}

      </Card>


      {/* ====================================================
          QUICK START
      ==================================================== */}

      {!search && (

        <section className="grid gap-4 md:grid-cols-3">

          <button
            type="button"
            onClick={() =>
              setActiveSection(
                'getting-started'
              )
            }
            className="rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-teal-200 hover:shadow-md"
          >

            <Zap
              size={22}
              className="text-teal-600"
            />


            <h2 className="mt-4 text-base font-semibold text-slate-900">
              Quick Start
            </h2>


            <p className="mt-2 text-sm leading-6 text-slate-500">
              Learn the basic FetalAI workflow from patient
              selection to the final report.
            </p>

          </button>


          <button
            type="button"
            onClick={() =>
              setActiveSection(
                'ai-analysis'
              )
            }
            className="rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md"
          >

            <Brain
              size={22}
              className="text-indigo-600"
            />


            <h2 className="mt-4 text-base font-semibold text-slate-900">
              Understand AI
            </h2>


            <p className="mt-2 text-sm leading-6 text-slate-500">
              Learn about confidence, brain analysis,
              statistical screening and Grad-CAM.
            </p>

          </button>


          <button
            type="button"
            onClick={() =>
              setActiveSection(
                'troubleshooting'
              )
            }
            className="rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-amber-200 hover:shadow-md"
          >

            <AlertCircle
              size={22}
              className="text-amber-600"
            />


            <h2 className="mt-4 text-base font-semibold text-slate-900">
              Troubleshooting
            </h2>


            <p className="mt-2 text-sm leading-6 text-slate-500">
              Find solutions for API, upload, analysis,
              Grad-CAM and report problems.
            </p>

          </button>

        </section>

      )}


      {/* ====================================================
          MAIN HELP AREA
      ==================================================== */}

      <div className="grid gap-6 lg:grid-cols-[250px_minmax(0,1fr)]">

        {/* ==================================================
            SIDEBAR
        ================================================== */}

        <Card>

          <div className="space-y-1">

            <p className="mb-3 px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
              Help topics
            </p>


            {filteredSections.map(
              (section) => {

                const Icon =
                  section.icon;

                const active =
                  activeSection ===
                  section.id;

                return (

                  <button
                    key={section.id}
                    type="button"
                    onClick={() =>
                      setActiveSection(
                        section.id
                      )
                    }
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition ${
                      active
                        ? 'bg-teal-50 font-medium text-teal-700'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    }`}
                  >

                    <Icon
                      size={17}
                      className={
                        active
                          ? 'text-teal-600'
                          : 'text-slate-400'
                      }
                    />


                    <span className="truncate">
                      {section.category}
                    </span>

                  </button>

                );

              }
            )}

          </div>

        </Card>


        {/* ==================================================
            CONTENT
        ================================================== */}

        <div className="space-y-5">

          {filteredSections.length ===
          0 ? (

            <Card>

              <div className="flex min-h-[300px] flex-col items-center justify-center text-center">

                <Search
                  size={36}
                  className="text-slate-300"
                />


                <h2 className="mt-4 text-base font-semibold text-slate-800">
                  No matching help topic
                </h2>


                <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
                  Try searching for terms such as
                  scan, patient, confidence, Grad-CAM,
                  report, password or API.
                </p>

              </div>

            </Card>

          ) : (

            filteredSections.map(
              (section) => {

                const Icon =
                  section.icon;

                const shouldShow =
                  search ||
                  activeSection ===
                    section.id;

                if (!shouldShow) {
                  return null;
                }

                return (

                  <Card
                    key={section.id}
                  >

                    {/* SECTION HEADER */}

                    <div className="mb-5 flex items-start gap-3">

                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-teal-50 text-teal-600">

                        <Icon
                          size={21}
                        />

                      </div>


                      <div>

                        <p className="text-xs font-semibold uppercase tracking-wider text-teal-600">
                          {section.category}
                        </p>


                        <h2 className="mt-1 text-lg font-semibold text-slate-900">
                          {section.title}
                        </h2>


                        <p className="mt-1 text-sm leading-6 text-slate-500">
                          {section.description}
                        </p>

                      </div>

                    </div>


                    {/* QUESTIONS */}

                    <div className="divide-y divide-slate-100 rounded-2xl border border-slate-200">

                      {section.content.map(
                        (item) => {

                          const isOpen =
                            openQuestions.has(
                              item.question
                            );

                          return (

                            <div
                              key={
                                item.question
                              }
                              className="bg-white first:rounded-t-2xl last:rounded-b-2xl"
                            >

                              <button
                                type="button"
                                onClick={() =>
                                  toggleQuestion(
                                    item.question
                                  )
                                }
                                className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition hover:bg-slate-50"
                              >

                                <span className="text-sm font-semibold text-slate-800">
                                  {item.question}
                                </span>


                                <ChevronDown
                                  size={18}
                                  className={`shrink-0 text-slate-400 transition-transform ${
                                    isOpen
                                      ? 'rotate-180'
                                      : ''
                                  }`}
                                />

                              </button>


                              {isOpen && (

                                <div className="border-t border-slate-100 px-5 py-4">

                                  <p className="text-sm leading-7 text-slate-600">
                                    {item.answer}
                                  </p>

                                </div>

                              )}

                            </div>

                          );

                        }
                      )}

                    </div>

                  </Card>

                );

              }
            )

          )}

        </div>

      </div>


      {/* ====================================================
          CLINICAL SAFETY NOTICE
      ==================================================== */}

      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5">

        <div className="flex items-start gap-3">

          <ShieldCheck
            size={20}
            className="mt-0.5 shrink-0 text-amber-700"
          />


          <div>

            <h2 className="text-sm font-semibold text-amber-900">
              Important clinical safety notice
            </h2>


            <p className="mt-2 text-xs leading-6 text-amber-800">

              FetalAI provides AI-assisted screening
              and statistical analysis outputs for
              clinical review. Model confidence,
              statistical outlier scores and Grad-CAM
              visualizations should not be interpreted
              as standalone clinically validated
              fetal anomaly diagnoses.

            </p>

          </div>

        </div>

      </div>


      {/* ====================================================
          SUPPORT CARD
      ==================================================== */}

      <Card>

        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">

          <div className="flex items-start gap-3">

            <div className="rounded-xl bg-slate-100 p-2.5">

              <HelpCircle
                size={20}
                className="text-slate-600"
              />

            </div>


            <div>

              <h2 className="text-sm font-semibold text-slate-900">
                Still need help?
              </h2>


              <p className="mt-1 text-sm leading-6 text-slate-500">
                If an issue is not covered here, provide the
                relevant scan ID, error message and backend
                log information to the system administrator.
              </p>

            </div>

          </div>


          <div className="flex items-center gap-2 rounded-xl bg-slate-50 px-4 py-3">

            <CheckCircle2
              size={17}
              className="text-emerald-600"
            />


            <span className="text-xs font-medium text-slate-600">
              FetalAI Help Center
            </span>

          </div>

        </div>

      </Card>

    </div>

  );
}