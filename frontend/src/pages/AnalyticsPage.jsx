import { useEffect, useMemo, useState } from 'react';

import {
  Activity,
  AlertTriangle,
  Brain,
  CheckCircle2,
  RefreshCw,
  ScanLine,
  TrendingUp,
  BarChart3,
} from 'lucide-react';

import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import { getScans } from '../services/api';


// ============================================================
// CONSTANTS
// ============================================================

const PLANES = [
  'Fetal brain',
  'Fetal abdomen',
  'Fetal thorax',
  'Fetal femur',
  'Maternal cervix',
  'Other',
];

const BRAIN_PLANES = [
  'Trans-thalamic',
  'Trans-cerebellum',
  'Trans-ventricular',
];


// ============================================================
// HELPERS
// ============================================================

function getAnalysis(scan) {
  return scan?.analysis_result || {};
}


function getFetalPlane(scan) {
  const analysis = getAnalysis(scan);

  return (
    analysis?.fetal_plane ||
    {}
  );
}


function getBrainPlane(scan) {
  const analysis = getAnalysis(scan);

  return (
    analysis?.brain_plane ||
    {}
  );
}


function getOutlierAnalysis(scan) {
  const analysis = getAnalysis(scan);

  return (
    analysis?.outlier_analysis ||
    null
  );
}


function isBrainClassified(scan) {
  const fetalPlane =
    getFetalPlane(scan);

  return (
    fetalPlane.predicted_class ===
    'Fetal brain'
  );
}


function isBrainAnalysisPerformed(scan) {
  const analysis =
    getAnalysis(scan);

  return (
    analysis.brain_analysis_performed ===
    true
  );
}


function isStatisticalOutlier(scan) {
  const outlier =
    getOutlierAnalysis(scan);

  if (!outlier) {
    return false;
  }

  // Primary source

  if (
    outlier.is_outlier === true
  ) {
    return true;
  }

  // Some model implementations may
  // return a status instead.

  const status = String(
    outlier.status || ''
  ).toLowerCase();

  return (
    status.includes('outlier') ||
    status.includes('unusual') ||
    status.includes('flagged')
  );
}


// ============================================================
// COMPONENT
// ============================================================

function AnalyticsPage() {
  const [scans, setScans] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState('');


  // ==========================================================
  // LOAD ANALYTICS
  // ==========================================================

  const loadAnalytics =
    async () => {
      try {
        setLoading(true);
        setError('');

        const data =
          await getScans();

        const scanList =
          Array.isArray(data)
            ? data
            : data?.scans || [];

        setScans(scanList);

      } catch (err) {
        console.error(
          'Analytics loading error:',
          err
        );

        setError(
          err.response?.data?.detail ||
          err.message ||
          'Unable to load analytics data.'
        );

      } finally {
        setLoading(false);
      }
    };


  // ==========================================================
  // INITIAL LOAD
  // ==========================================================

  useEffect(() => {
    loadAnalytics();
  }, []);


  // ==========================================================
  // BASIC STATISTICS
  // ==========================================================

  const stats =
    useMemo(() => {

      const total =
        scans.length;


      const brainClassified =
        scans.filter(
          (scan) =>
            isBrainClassified(scan)
        ).length;


      const brainAnalysisPerformed =
        scans.filter(
          (scan) =>
            isBrainAnalysisPerformed(
              scan
            )
        ).length;


      const statisticalAnalysis =
        scans.filter(
          (scan) =>
            Boolean(
              getOutlierAnalysis(scan)
            )
        ).length;


      const flagged =
        scans.filter(
          (scan) =>
            isStatisticalOutlier(
              scan
            )
        ).length;


      // ------------------------------------------------------
      // FETAL PLANE CONFIDENCE
      // ------------------------------------------------------

      const confidenceValues =
        scans
          .map((scan) => {

            const fetalPlane =
              getFetalPlane(scan);

            const value =
              Number(
                fetalPlane.confidence ??
                scan.confidence ??
                0
              );

            return Number.isFinite(
              value
            )
              ? value
              : 0;
          });


      const confidence =
        total > 0
          ? confidenceValues.reduce(
              (sum, value) =>
                sum + value,
              0
            ) / total
          : 0;


      // ------------------------------------------------------
      // BRAIN ANALYSIS RATE
      // ------------------------------------------------------

      const brainAnalysisRate =
        brainClassified > 0
          ? (
              brainAnalysisPerformed /
              brainClassified
            ) * 100
          : 0;


      return {
        total,

        brainClassified,

        brainAnalysisPerformed,

        statisticalAnalysis,

        flagged,

        confidence,

        brainAnalysisRate,
      };

    }, [scans]);


  // ==========================================================
  // FETAL PLANE DISTRIBUTION
  // ==========================================================

  const planeDistribution =
    useMemo(() => {

      return PLANES.map(
        (plane) => {

          const count =
            scans.filter(
              (scan) => {

                const fetalPlane =
                  getFetalPlane(scan);

                return (
                  fetalPlane.predicted_class ===
                  plane
                );
              }
            ).length;


          return {
            plane,

            count,

            percentage:
              scans.length > 0
                ? (
                    count /
                    scans.length
                  ) * 100
                : 0,
          };
        }
      );

    }, [scans]);


  // ==========================================================
  // BRAIN PLANE DISTRIBUTION
  // ==========================================================

  const brainPlaneDistribution =
    useMemo(() => {

      return BRAIN_PLANES.map(
        (plane) => {

          const count =
            scans.filter(
              (scan) => {

                const brainPlane =
                  getBrainPlane(scan);

                return (
                  isBrainAnalysisPerformed(
                    scan
                  ) &&
                  brainPlane.predicted_class ===
                  plane
                );
              }
            ).length;


          return {
            plane,

            count,

            percentage:
              stats.brainAnalysisPerformed >
              0
                ? (
                    count /
                    stats.brainAnalysisPerformed
                  ) * 100
                : 0,
          };
        }
      );

    }, [
      scans,
      stats.brainAnalysisPerformed,
    ]);


  // ==========================================================
  // MONTHLY TREND
  // ==========================================================

  const monthlyData =
    useMemo(() => {

      const months = [];

      for (
        let i = 5;
        i >= 0;
        i -= 1
      ) {

        const date =
          new Date();

        date.setMonth(
          date.getMonth() - i
        );


        months.push({
          key: `${date.getFullYear()}-${date.getMonth()}`,

          month:
            date.toLocaleString(
              'en-US',
              {
                month: 'short',
              }
            ),

          count: 0,
        });
      }


      scans.forEach(
        (scan) => {

          if (!scan.created_at) {
            return;
          }


          const date =
            new Date(
              scan.created_at
            );


          if (
            Number.isNaN(
              date.getTime()
            )
          ) {
            return;
          }


          const key =
            `${date.getFullYear()}-${date.getMonth()}`;


          const month =
            months.find(
              (item) =>
                item.key === key
            );


          if (month) {
            month.count += 1;
          }
        }
      );


      return months;

    }, [scans]);


  const maxMonthly =
    Math.max(
      ...monthlyData.map(
        (item) =>
          item.count
      ),
      1
    );


  // ==========================================================
  // BRAIN SCANS
  // ==========================================================

  const brainScans =
    useMemo(
      () =>
        scans.filter(
          (scan) =>
            isBrainClassified(
              scan
            )
        ),
      [scans]
    );


  // ==========================================================
  // BRAIN CONFIDENCE
  // ==========================================================

  const brainConfidence =
    useMemo(() => {

      const values =
        brainScans
          .filter(
            (scan) =>
              isBrainAnalysisPerformed(
                scan
              )
          )
          .map(
            (scan) =>
              Number(
                getBrainPlane(
                  scan
                ).confidence || 0
              )
          )
          .filter(
            (value) =>
              Number.isFinite(
                value
              )
          );


      if (!values.length) {
        return 0;
      }


      return (
        values.reduce(
          (sum, value) =>
            sum + value,
          0
        ) /
        values.length
      );

    }, [brainScans]);


  // ==========================================================
  // TODAY'S SCANS
  // ==========================================================

  const todaysScans =
    useMemo(() => {

      const now =
        new Date();

      return scans.filter(
        (scan) => {

          if (!scan.created_at) {
            return false;
          }

          const date =
            new Date(
              scan.created_at
            );

          return (
            date.getFullYear() ===
              now.getFullYear() &&
            date.getMonth() ===
              now.getMonth() &&
            date.getDate() ===
              now.getDate()
          );
        }
      ).length;

    }, [scans]);


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="space-y-6">

      {/* ====================================================
          HEADER
      ==================================================== */}

      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">

        <div>

          <h1 className="text-2xl font-semibold text-slate-900">
            Analytics
          </h1>

          <p className="mt-2 text-slate-500">
            Real-time analytics based on completed ultrasound scans.
          </p>

        </div>


        <Button
          variant="secondary"
          onClick={
            loadAnalytics
          }
          disabled={loading}
        >

          <RefreshCw
            size={17}
            className={`mr-2 ${
              loading
                ? 'animate-spin'
                : ''
            }`}
          />

          Refresh

        </Button>

      </div>


      {/* ====================================================
          ERROR
      ==================================================== */}

      {error && (

        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">

          {error}

        </div>

      )}


      {/* ====================================================
          SUMMARY CARDS
      ==================================================== */}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

        {/* TOTAL SCANS */}

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

          <div className="flex items-start justify-between">

            <div>

              <p className="text-sm text-slate-500">
                Total Scans
              </p>

              <p className="mt-3 text-3xl font-semibold text-slate-900">
                {loading
                  ? '—'
                  : stats.total}
              </p>

            </div>

            <div className="rounded-xl bg-cyan-50 p-3 text-cyan-700">

              <ScanLine
                size={21}
              />

            </div>

          </div>

          <p className="mt-4 text-xs text-slate-400">
            All completed analyses
          </p>

        </div>


        {/* BRAIN SCANS */}

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

          <div className="flex items-start justify-between">

            <div>

              <p className="text-sm text-slate-500">
                Fetal Brain Scans
              </p>

              <p className="mt-3 text-3xl font-semibold text-slate-900">
                {loading
                  ? '—'
                  : stats.brainClassified}
              </p>

            </div>

            <div className="rounded-xl bg-violet-50 p-3 text-violet-700">

              <Brain
                size={21}
              />

            </div>

          </div>

          <p className="mt-4 text-xs text-slate-400">
            Classified as fetal brain
          </p>

        </div>


        {/* CONFIDENCE */}

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

          <div className="flex items-start justify-between">

            <div>

              <p className="text-sm text-slate-500">
                Average Confidence
              </p>

              <p className="mt-3 text-3xl font-semibold text-slate-900">
                {loading
                  ? '—'
                  : `${(
                      stats.confidence *
                      100
                    ).toFixed(1)}%`}
              </p>

            </div>

            <div className="rounded-xl bg-emerald-50 p-3 text-emerald-700">

              <TrendingUp
                size={21}
              />

            </div>

          </div>

          <p className="mt-4 text-xs text-slate-400">
            Across fetal-plane classifications
          </p>

        </div>


        {/* FLAGGED */}

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

          <div className="flex items-start justify-between">

            <div>

              <p className="text-sm text-slate-500">
                Flagged Results
              </p>

              <p className="mt-3 text-3xl font-semibold text-slate-900">
                {loading
                  ? '—'
                  : stats.flagged}
              </p>

            </div>

            <div className="rounded-xl bg-amber-50 p-3 text-amber-700">

              <AlertTriangle
                size={21}
              />

            </div>

          </div>

          <p className="mt-4 text-xs text-slate-400">
            Statistical outlier results
          </p>

        </div>

      </section>


      {/* ====================================================
          SECONDARY STATS
      ==================================================== */}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <div className="rounded-2xl border border-slate-200 bg-white p-5">

          <p className="text-sm text-slate-500">
            Today's Scans
          </p>

          <p className="mt-2 text-2xl font-semibold text-slate-900">
            {loading
              ? '—'
              : todaysScans}
          </p>

        </div>


        <div className="rounded-2xl border border-slate-200 bg-white p-5">

          <p className="text-sm text-slate-500">
            Brain Analysis Performed
          </p>

          <p className="mt-2 text-2xl font-semibold text-slate-900">
            {loading
              ? '—'
              : stats.brainAnalysisPerformed}
          </p>

        </div>


        <div className="rounded-2xl border border-slate-200 bg-white p-5">

          <p className="text-sm text-slate-500">
            Brain Analysis Rate
          </p>

          <p className="mt-2 text-2xl font-semibold text-slate-900">
            {loading
              ? '—'
              : `${stats.brainAnalysisRate.toFixed(
                  1
                )}%`}
          </p>

        </div>


        <div className="rounded-2xl border border-slate-200 bg-white p-5">

          <p className="text-sm text-slate-500">
            Statistical Analysis
          </p>

          <p className="mt-2 text-2xl font-semibold text-slate-900">
            {loading
              ? '—'
              : stats.statisticalAnalysis}
          </p>

        </div>

      </section>


      {/* ====================================================
          MAIN ANALYTICS
      ==================================================== */}

      <section className="grid gap-6 xl:grid-cols-2">

        {/* FETAL PLANE */}

        <Card
          title="Fetal Plane Distribution"
          subtitle="Classification breakdown across all scans."
        >

          {scans.length === 0 ? (

            <div className="flex h-72 flex-col items-center justify-center rounded-2xl bg-slate-50 text-center">

              <Brain
                size={32}
                className="text-slate-400"
              />

              <p className="mt-3 text-sm font-medium text-slate-700">
                No classification data
              </p>

              <p className="mt-1 text-xs text-slate-500">
                Upload an ultrasound scan to populate analytics.
              </p>

            </div>

          ) : (

            <div className="space-y-5">

              {planeDistribution.map(
                (item) => (

                  <div
                    key={
                      item.plane
                    }
                  >

                    <div className="flex items-center justify-between">

                      <span className="text-sm font-medium text-slate-700">
                        {item.plane}
                      </span>

                      <span className="text-sm font-semibold text-slate-900">
                        {item.count}
                      </span>

                    </div>


                    <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100">

                      <div
                        className="h-full rounded-full bg-cyan-500 transition-all"
                        style={{
                          width: `${item.percentage}%`,
                        }}
                      />

                    </div>


                    <p className="mt-1 text-xs text-slate-400">
                      {item.percentage.toFixed(
                        1
                      )}
                      %
                    </p>

                  </div>

                )
              )}

            </div>

          )}

        </Card>


        {/* MONTHLY TREND */}

        <Card
          title="Monthly Scan Trend"
          subtitle="Number of scans processed each month."
        >

          <div className="flex h-72 items-end gap-4 rounded-2xl bg-slate-50 p-6">

            {monthlyData.map(
              (item) => (

                <div
                  key={
                    item.key
                  }
                  className="flex flex-1 flex-col items-center justify-end gap-3"
                >

                  <span className="text-xs font-medium text-slate-600">
                    {item.count}
                  </span>


                  <div
                    className="w-full max-w-12 rounded-t-xl bg-cyan-500 transition-all"
                    style={{
                      height: `${Math.max(
                        (
                          item.count /
                          maxMonthly
                        ) * 150,

                        item.count > 0
                          ? 16
                          : 5
                      )}px`,
                    }}
                  />


                  <span className="text-xs text-slate-500">
                    {item.month}
                  </span>

                </div>

              )
            )}

          </div>

        </Card>

      </section>


      {/* ====================================================
          BRAIN ANALYTICS
      ==================================================== */}

      <section className="grid gap-6 xl:grid-cols-2">

        {/* BRAIN OVERVIEW */}

        <Card
          title="Brain Scan Overview"
          subtitle="Statistics for images classified as fetal brain."
        >

          <div className="grid gap-4 sm:grid-cols-2">

            <div className="rounded-2xl bg-violet-50 p-5">

              <Brain
                size={24}
                className="text-violet-700"
              />

              <p className="mt-4 text-sm text-slate-500">
                Brain scans
              </p>

              <p className="mt-1 text-2xl font-semibold text-slate-900">
                {stats.brainClassified}
              </p>

            </div>


            <div className="rounded-2xl bg-emerald-50 p-5">

              <CheckCircle2
                size={24}
                className="text-emerald-700"
              />

              <p className="mt-4 text-sm text-slate-500">
                Brain confidence
              </p>

              <p className="mt-1 text-2xl font-semibold text-slate-900">
                {(
                  brainConfidence *
                  100
                ).toFixed(2)}
                %
              </p>

            </div>

          </div>


          <div className="mt-5 rounded-xl border border-slate-200 p-4">

            <div className="flex items-center gap-2">

              <Brain
                size={17}
                className="text-violet-600"
              />

              <p className="text-sm font-semibold text-slate-800">
                Brain Plane Distribution
              </p>

            </div>


            <div className="mt-4 space-y-4">

              {brainPlaneDistribution.map(
                (item) => (

                  <div
                    key={
                      item.plane
                    }
                  >

                    <div className="flex items-center justify-between">

                      <span className="text-sm text-slate-600">
                        {item.plane}
                      </span>

                      <span className="text-sm font-semibold text-slate-900">
                        {item.count}
                      </span>

                    </div>


                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">

                      <div
                        className="h-full rounded-full bg-violet-500 transition-all"
                        style={{
                          width: `${item.percentage}%`,
                        }}
                      />

                    </div>

                  </div>

                )
              )}

            </div>

          </div>

        </Card>


        {/* STATISTICAL ANALYSIS */}

        <Card
          title="Statistical Analysis"
          subtitle="Outlier information returned by the AI pipeline."
        >

          {stats.brainAnalysisPerformed ===
          0 ? (

            <div className="flex h-48 flex-col items-center justify-center rounded-2xl bg-slate-50 text-center">

              <Activity
                size={30}
                className="text-slate-400"
              />

              <p className="mt-3 text-sm font-medium text-slate-700">
                No brain analysis available
              </p>

              <p className="mt-1 max-w-sm text-xs leading-5 text-slate-500">
                Brain-specific statistical analysis
                becomes available when an image is
                classified as fetal brain with sufficient
                confidence.
              </p>

            </div>

          ) : (

            <div className="space-y-3">

              <div className="flex items-center justify-between rounded-xl border border-slate-200 p-4">

                <span className="text-sm text-slate-500">
                  Brain analyses
                </span>

                <span className="font-semibold text-slate-900">
                  {
                    stats.brainAnalysisPerformed
                  }
                </span>

              </div>


              <div className="flex items-center justify-between rounded-xl border border-slate-200 p-4">

                <span className="text-sm text-slate-500">
                  Statistical analyses
                </span>

                <span className="font-semibold text-slate-900">
                  {
                    stats.statisticalAnalysis
                  }
                </span>

              </div>


              <div className="flex items-center justify-between rounded-xl border border-slate-200 p-4">

                <span className="text-sm text-slate-500">
                  Flagged outliers
                </span>

                <span className="font-semibold text-rose-600">
                  {stats.flagged}
                </span>

              </div>


              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">

                <div className="flex gap-3">

                  <AlertTriangle
                    size={19}
                    className="mt-0.5 shrink-0 text-amber-700"
                  />

                  <p className="text-xs leading-5 text-amber-800">
                    Outlier scores are statistical
                    indicators from the experimental
                    pipeline and are not medical diagnoses.
                  </p>

                </div>

              </div>

            </div>

          )}

        </Card>

      </section>


      {/* ====================================================
          AI PIPELINE SUMMARY
      ==================================================== */}

      <Card
        title="AI Pipeline Summary"
        subtitle="Current scan-processing coverage."
      >

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

          <div className="rounded-2xl bg-slate-50 p-5">

            <ScanLine
              size={22}
              className="text-cyan-600"
            />

            <p className="mt-4 text-xs text-slate-500">
              Fetal Plane Classification
            </p>

            <p className="mt-1 font-semibold text-emerald-600">
              Active
            </p>

          </div>


          <div className="rounded-2xl bg-slate-50 p-5">

            <Brain
              size={22}
              className="text-violet-600"
            />

            <p className="mt-4 text-xs text-slate-500">
              Brain Plane Classification
            </p>

            <p className="mt-1 font-semibold text-emerald-600">
              Conditional
            </p>

          </div>


          <div className="rounded-2xl bg-slate-50 p-5">

            <BarChart3
              size={22}
              className="text-amber-600"
            />

            <p className="mt-4 text-xs text-slate-500">
              Statistical Screening
            </p>

            <p className="mt-1 font-semibold text-emerald-600">
              Conditional
            </p>

          </div>


          <div className="rounded-2xl bg-slate-50 p-5">

            <Activity
              size={22}
              className="text-teal-600"
            />

            <p className="mt-4 text-xs text-slate-500">
              Total Analyses
            </p>

            <p className="mt-1 font-semibold text-slate-900">
              {stats.total}
            </p>

          </div>

        </div>

      </Card>


      {/* ====================================================
          DISCLAIMER
      ==================================================== */}

      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">

        <div className="flex gap-3">

          <AlertTriangle
            size={18}
            className="mt-0.5 shrink-0 text-amber-700"
          />

          <p className="text-xs leading-5 text-amber-800">
            FetalAI analytics are based on experimental
            AI-assisted screening outputs. Statistical
            results should be reviewed by a qualified
            healthcare professional and must not be treated
            as a clinically validated diagnosis.
          </p>

        </div>

      </div>

    </div>
  );
}


export default AnalyticsPage;