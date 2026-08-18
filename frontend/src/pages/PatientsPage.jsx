import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  Plus,
  RefreshCw,
  UserRound,
  Search,
  Activity,
  Brain,
  BarChart3,
  CalendarDays,
  FileText,
  Eye,
  X,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';

import Card from '../components/ui/Card';
import Button from '../components/ui/Button';

import {
  getPatients,
  createPatient,
  getPatientScans,
} from '../services/api';


// ============================================================
// HELPERS
// ============================================================

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') {
          return item;
        }

        const field = Array.isArray(item?.loc)
          ? item.loc[item.loc.length - 1]
          : 'field';

        return `${field}: ${
          item?.msg || 'Invalid value'
        }`;
      })
      .join(' | ');
  }

  if (typeof detail === 'string') {
    return detail;
  }

  return (
    error?.response?.data?.message ||
    error?.message ||
    fallback
  );
}


function formatDate(value) {
  if (!value) {
    return '—';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return '—';
  }

  return date.toLocaleString();
}


function formatPercentage(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return '—';
  }

  const percentage =
    number <= 1
      ? number * 100
      : number;

  return `${percentage.toFixed(2)}%`;
}


// ============================================================
// PATIENTS PAGE
// ============================================================

function PatientsPage() {
  const navigate = useNavigate();
  // ==========================================================
  // PATIENTS
  // ==========================================================

  const [patients, setPatients] = useState([]);

  const [loading, setLoading] =
    useState(true);

  const [creating, setCreating] =
    useState(false);

  const [error, setError] =
    useState('');

  const [success, setSuccess] =
    useState('');

  const [search, setSearch] =
    useState('');


  // ==========================================================
  // SELECTED PATIENT
  // ==========================================================

  const [selectedPatient, setSelectedPatient] =
    useState(null);

  const [patientScans, setPatientScans] =
    useState([]);

  const [loadingScans, setLoadingScans] =
    useState(false);

  const [scanError, setScanError] =
    useState('');


  // ==========================================================
  // FORM
  // ==========================================================

  const [form, setForm] = useState({
    patient_id: '',
    full_name: '',
    age: '',
    gestational_age: '',
    phone: '',
  });


  // ==========================================================
  // LOAD PATIENTS
  // ==========================================================

  const loadPatients = async () => {
    setLoading(true);
    setError('');

    try {
      const response =
        await getPatients();

      const data =
        Array.isArray(response)
          ? response
          : response?.patients || [];

      setPatients(data);
    } catch (err) {
      console.error(
        'Failed to load patients:',
        err
      );

      setError(
        getErrorMessage(
          err,
          'Failed to load patients.'
        )
      );
    } finally {
      setLoading(false);
    }
  };


  // ==========================================================
  // INITIAL LOAD
  // ==========================================================

  useEffect(() => {
    loadPatients();
  }, []);


  // ==========================================================
  // FORM CHANGE
  // ==========================================================

  const handleChange = (event) => {
    const {
      name,
      value,
    } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));

    setError('');
    setSuccess('');
  };


  // ==========================================================
  // CREATE PATIENT
  // ==========================================================

  const handleCreatePatient =
    async (event) => {
      event.preventDefault();

      setError('');
      setSuccess('');

      if (
        !form.patient_id.trim() ||
        !form.full_name.trim() ||
        !form.age ||
        !form.gestational_age.trim()
      ) {
        setError(
          'Patient ID, full name, age, and gestational age are required.'
        );

        return;
      }

      const age = Number(form.age);

      if (
        !Number.isInteger(age) ||
        age <= 0 ||
        age > 120
      ) {
        setError(
          'Please enter a valid age.'
        );

        return;
      }

      setCreating(true);

      try {
        await createPatient({
          patient_id:
            form.patient_id.trim(),

          full_name:
            form.full_name.trim(),

          age,

          gestational_age:
            form.gestational_age.trim(),

          phone:
            form.phone.trim() || null,
        });

        setForm({
          patient_id: '',
          full_name: '',
          age: '',
          gestational_age: '',
          phone: '',
        });

        setSuccess(
          'Patient created successfully.'
        );

        await loadPatients();
      } catch (err) {
        console.error(
          'Failed to create patient:',
          err
        );

        setError(
          getErrorMessage(
            err,
            'Failed to create patient.'
          )
        );
      } finally {
        setCreating(false);
      }
    };


  // ==========================================================
  // LOAD PATIENT SCANS
  // ==========================================================

  const handleSelectPatient =
    async (patient) => {
      setSelectedPatient(patient);

      setPatientScans([]);

      setScanError('');

      setLoadingScans(true);

      try {
        const response =
          await getPatientScans(
            patient.patient_id
          );

        const scans =
          Array.isArray(response)
            ? response
            : response?.scans || [];

        setPatientScans(scans);
      } catch (err) {
        console.error(
          'Failed to load patient scans:',
          err
        );

        setScanError(
          getErrorMessage(
            err,
            'Failed to load patient scan history.'
          )
        );
      } finally {
        setLoadingScans(false);
      }
    };


  // ==========================================================
  // CLOSE PATIENT DETAILS
  // ==========================================================

  const handleClosePatient = () => {
    setSelectedPatient(null);
    setPatientScans([]);
    setScanError('');
  };


  // ==========================================================
  // SEARCH
  // ==========================================================

  const filteredPatients = useMemo(() => {
    const value =
      search.toLowerCase().trim();

    if (!value) {
      return patients;
    }

    return patients.filter(
      (patient) =>
        String(
          patient.patient_id || ''
        )
          .toLowerCase()
          .includes(value) ||

        String(
          patient.full_name || ''
        )
          .toLowerCase()
          .includes(value)
    );
  }, [
    patients,
    search,
  ]);


  // ==========================================================
  // SCAN SORT
  // ==========================================================

  const sortedScans = useMemo(() => {
    return [...patientScans].sort(
      (a, b) =>
        new Date(
          b.created_at || 0
        ) -
        new Date(
          a.created_at || 0
        )
    );
  }, [patientScans]);


  // ==========================================================
  // SCAN STATS
  // ==========================================================

  const totalScans =
    sortedScans.length;

  const brainScans =
    sortedScans.filter(
      (scan) =>
        String(
          scan.predicted_plane || ''
        ).toLowerCase() ===
        'fetal brain'
    ).length;

  const latestScan =
    sortedScans[0] || null;


  // ==========================================================
  // OPEN REPORT
  // ==========================================================

  const handleOpenReport = (
    scanId
  ) => {
    if (!scanId) {
      return;
    }

    navigate(
      `/reports?scan=${encodeURIComponent(
        scanId
      )}`
    );
  };


  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="space-y-6 p-6">

      {/* ======================================================
          HEADER
      ====================================================== */}

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">

        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            Patients
          </h1>

          <p className="mt-1 text-sm text-slate-500">
            Manage patients and their ultrasound studies.
          </p>
        </div>


        <Button
          type="button"
          variant="secondary"
          onClick={loadPatients}
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


      {/* ======================================================
          ERROR
      ====================================================== */}

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}


      {/* ======================================================
          SUCCESS
      ====================================================== */}

      {success && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {success}
        </div>
      )}


      {/* ======================================================
          MAIN GRID
      ====================================================== */}

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">

        {/* ====================================================
            ADD PATIENT
        ==================================================== */}

        <Card
          title="Add Patient"
          subtitle="Create a patient record before uploading a scan."
        >

          <form
            onSubmit={
              handleCreatePatient
            }
            className="mt-5 space-y-4"
          >

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Patient ID
              </label>

              <input
                name="patient_id"
                value={
                  form.patient_id
                }
                onChange={
                  handleChange
                }
                placeholder="PAT002"
                disabled={creating}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              />
            </div>


            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Full Name
              </label>

              <input
                name="full_name"
                value={
                  form.full_name
                }
                onChange={
                  handleChange
                }
                placeholder="Patient name"
                disabled={creating}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              />
            </div>


            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Age
              </label>

              <input
                name="age"
                type="number"
                min="1"
                max="120"
                value={form.age}
                onChange={
                  handleChange
                }
                placeholder="28"
                disabled={creating}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              />
            </div>


            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Gestational Age
              </label>

              <input
                name="gestational_age"
                value={
                  form.gestational_age
                }
                onChange={
                  handleChange
                }
                placeholder="24w 3d"
                disabled={creating}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              />
            </div>


            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Phone
                <span className="ml-1 font-normal text-slate-400">
                  (optional)
                </span>
              </label>

              <input
                name="phone"
                type="tel"
                value={form.phone}
                onChange={
                  handleChange
                }
                placeholder="9876543210"
                disabled={creating}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
              />
            </div>


            <Button
              type="submit"
              disabled={creating}
              className="w-full"
            >
              <Plus
                size={17}
                className="mr-2"
              />

              {creating
                ? 'Creating...'
                : 'Create Patient'}
            </Button>

          </form>

        </Card>


        {/* ====================================================
            PATIENT RECORDS
        ==================================================== */}

        <Card
          title="Patient Records"
          subtitle={`${patients.length} patient${
            patients.length === 1
              ? ''
              : 's'
          } available`}
        >

          <div className="mt-5 relative">

            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />

            <input
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value
                )
              }
              placeholder="Search by patient ID or name..."
              className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-4 text-sm outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
            />

          </div>


          <div className="mt-5 overflow-hidden rounded-xl border border-slate-200">

            {loading ? (

              <div className="flex items-center justify-center p-10 text-sm text-slate-500">
                Loading patients...
              </div>

            ) : filteredPatients.length === 0 ? (

              <div className="flex flex-col items-center justify-center p-10 text-center">

                <UserRound
                  size={36}
                  className="text-slate-300"
                />

                <p className="mt-3 text-sm font-medium text-slate-700">
                  No patients found
                </p>

                <p className="mt-1 text-xs text-slate-500">
                  Create a patient or change your search.
                </p>

              </div>

            ) : (

              <div className="divide-y divide-slate-200">

                {filteredPatients.map(
                  (patient) => {

                    const selected =
                      selectedPatient?.patient_id ===
                      patient.patient_id;

                    return (
                      <button
                        key={
                          patient.id ||
                          patient.patient_id
                        }
                        type="button"
                        onClick={() =>
                          handleSelectPatient(
                            patient
                          )
                        }
                        className={`flex w-full items-center justify-between gap-4 p-4 text-left transition ${
                          selected
                            ? 'bg-teal-50'
                            : 'bg-white hover:bg-slate-50'
                        }`}
                      >

                        <div className="flex items-center gap-3">

                          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
                            <UserRound
                              size={19}
                            />
                          </div>

                          <div>

                            <p className="text-sm font-semibold text-slate-900">
                              {patient.full_name ||
                                'Unnamed Patient'}
                            </p>

                            <p className="mt-1 text-xs text-slate-500">
                              {patient.patient_id}
                            </p>

                            <p className="mt-1 text-xs text-slate-400">
                              Age {patient.age}
                              {' · '}
                              {patient.gestational_age}
                            </p>

                          </div>

                        </div>


                        <div className="flex items-center gap-2">

                          <span className="hidden rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 sm:inline-flex">
                            Active
                          </span>

                          <Eye
                            size={17}
                            className="text-slate-400"
                          />

                        </div>

                      </button>
                    );
                  }
                )}

              </div>

            )}

          </div>

        </Card>

      </div>


      {/* ======================================================
          PATIENT SCAN HISTORY
      ====================================================== */}

      {selectedPatient && (

        <Card>

          <div className="flex flex-col gap-4 border-b border-slate-200 pb-5 md:flex-row md:items-center md:justify-between">

            <div className="flex items-center gap-3">

              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
                <UserRound
                  size={21}
                />
              </div>

              <div>

                <p className="text-xs font-semibold uppercase tracking-wide text-teal-600">
                  Patient Overview
                </p>

                <h2 className="mt-1 text-xl font-semibold text-slate-900">
                  {selectedPatient.full_name}
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  {selectedPatient.patient_id}
                  {' · '}
                  Age {selectedPatient.age}
                  {' · '}
                  {selectedPatient.gestational_age}
                  {selectedPatient.phone
                    ? ` · ${selectedPatient.phone}`
                    : ''}
                </p>

              </div>

            </div>


            <Button
              type="button"
              variant="secondary"
              onClick={
                handleClosePatient
              }
            >
              <X
                size={16}
                className="mr-2"
              />

              Close
            </Button>

          </div>


          {/* ==================================================
              STATS
          ================================================== */}

          <div className="mt-5 grid gap-4 sm:grid-cols-3">

            <div className="rounded-xl bg-slate-50 p-4">

              <div className="flex items-center gap-3">

                <Activity
                  size={20}
                  className="text-teal-600"
                />

                <div>

                  <p className="text-xs text-slate-500">
                    Total Scans
                  </p>

                  <p className="mt-1 text-xl font-semibold text-slate-900">
                    {totalScans}
                  </p>

                </div>

              </div>

            </div>


            <div className="rounded-xl bg-slate-50 p-4">

              <div className="flex items-center gap-3">

                <Brain
                  size={20}
                  className="text-indigo-600"
                />

                <div>

                  <p className="text-xs text-slate-500">
                    Brain Scans
                  </p>

                  <p className="mt-1 text-xl font-semibold text-slate-900">
                    {brainScans}
                  </p>

                </div>

              </div>

            </div>


            <div className="rounded-xl bg-slate-50 p-4">

              <div className="flex items-center gap-3">

                <CalendarDays
                  size={20}
                  className="text-emerald-600"
                />

                <div className="min-w-0">

                  <p className="text-xs text-slate-500">
                    Latest Scan
                  </p>

                  <p className="mt-1 truncate text-sm font-semibold text-slate-900">
                    {latestScan
                      ? formatDate(
                          latestScan.created_at
                        )
                      : 'No scans'}
                  </p>

                </div>

              </div>

            </div>

          </div>


          {/* ==================================================
              SCAN ERROR
          ================================================== */}

          {scanError && (

            <div className="mt-5 flex items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">

              <AlertTriangle
                size={18}
              />

              {scanError}

            </div>

          )}


          {/* ==================================================
              SCAN HISTORY
          ================================================== */}

          <div className="mt-6">

            <div className="flex items-center justify-between gap-4">

              <div>

                <h3 className="text-lg font-semibold text-slate-900">
                  Scan History
                </h3>

                <p className="mt-1 text-xs text-slate-500">
                  Previous ultrasound analyses for this patient.
                </p>

              </div>


              <Button
                type="button"
                variant="secondary"
                disabled={loadingScans}
                onClick={() =>
                  handleSelectPatient(
                    selectedPatient
                  )
                }
              >

                <RefreshCw
                  size={15}
                  className={`mr-2 ${
                    loadingScans
                      ? 'animate-spin'
                      : ''
                  }`}
                />

                Refresh

              </Button>

            </div>


            {loadingScans ? (

              <div className="mt-5 flex items-center justify-center rounded-xl border border-slate-200 bg-slate-50 p-10 text-sm text-slate-500">

                <RefreshCw
                  size={18}
                  className="mr-2 animate-spin"
                />

                Loading scan history...

              </div>

            ) : sortedScans.length === 0 ? (

              <div className="mt-5 flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-slate-50 p-10 text-center">

                <Activity
                  size={34}
                  className="text-slate-300"
                />

                <p className="mt-3 font-semibold text-slate-700">
                  No scans found
                </p>

                <p className="mt-1 text-sm text-slate-500">
                  This patient does not have completed scans yet.
                </p>

              </div>

            ) : (

              <div className="mt-5 space-y-3">

                {sortedScans.map(
                  (scan) => {

                    const analysis =
                      scan.analysis_result ||
                      scan.analysis ||
                      {};

                    const brainPlane =
                      analysis.brain_plane ||
                      analysis.brain ||
                      null;

                    const outlier =
                      analysis.outlier_analysis ||
                      analysis.outlier ||
                      null;

                    const screeningStatus =
                      outlier?.status ||
                      'Not available';

                    return (
                      <div
                        key={scan.id}
                        className="rounded-xl border border-slate-200 bg-white p-5"
                      >

                        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

                          <div className="flex items-center gap-3">

                            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700">

                              <Activity
                                size={19}
                              />

                            </div>

                            <div>

                              <div className="flex items-center gap-2">

                                <h4 className="font-semibold text-slate-900">
                                  Scan #{scan.id}
                                </h4>

                                <span
                                  className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                                    isOutlier
                                      ? 'bg-amber-50 text-amber-700'
                                      : analysisComplete
                                        ? 'bg-emerald-50 text-emerald-700'
                                        : 'bg-slate-100 text-slate-600'
                                  }`}
                                >
                                  {isOutlier
                                    ? 'Review'
                                    : analysisComplete
                                      ? 'Completed'
                                      : 'Pending'}
                                </span>

                              </div>

                              <p className="mt-1 text-xs text-slate-500">
                                {formatDate(
                                  scan.created_at
                                )}
                              </p>

                            </div>

                          </div>


                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() =>
                              handleOpenReport(
                                scan.id
                              )
                            }
                          >

                            <FileText
                              size={16}
                              className="mr-2"
                            />

                            Full Report

                          </Button>

                        </div>


                        {/* SCAN DATA */}

                        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">

                          <div className="rounded-xl bg-slate-50 p-4">

                            <p className="text-xs text-slate-500">
                              Fetal Plane
                            </p>

                            <p className="mt-1 font-semibold text-slate-900">
                              {scan.predicted_plane ||
                                '—'}
                            </p>

                            <p className="mt-1 text-xs text-teal-600">
                              {formatPercentage(
                                scan.confidence
                              )}
                            </p>

                          </div>


                          <div className="rounded-xl bg-indigo-50 p-4">

                            <div className="flex items-center gap-2">

                              <Brain
                                size={14}
                                className="text-indigo-600"
                              />

                              <p className="text-xs text-indigo-600">
                                Brain Plane
                              </p>

                            </div>

                            <p className="mt-1 font-semibold text-slate-900">
                              {brainPlane?.predicted_class ||
                                'Not applicable'}
                            </p>

                            {brainPlane && (
                              <p className="mt-1 text-xs text-indigo-600">
                                {formatPercentage(
                                  brainPlane.confidence_percent ??
                                  brainPlane.confidence
                                )}
                              </p>
                            )}

                          </div>


                          <div className="rounded-xl bg-emerald-50 p-4">

                            <div className="flex items-center gap-2">

                              <BarChart3
                                size={14}
                                className="text-emerald-600"
                              />

                              <p className="text-xs text-emerald-700">
                                Statistical Screening
                              </p>

                            </div>

                            <p className="mt-1 font-semibold text-slate-900">
                              {screeningStatus}
                            </p>

                            {outlier?.anomaly_score !==
                              undefined && (
                              <p className="mt-1 text-xs text-slate-500">
                                Score:{' '}
                                {
                                  outlier.anomaly_score
                                }
                              </p>
                            )}

                          </div>


                          <div className="rounded-xl bg-violet-50 p-4">

                            <div className="flex items-center gap-2">

                              <Eye
                                size={14}
                                className="text-violet-600"
                              />

                              <p className="text-xs text-violet-600">
                                Explainability
                              </p>

                            </div>

                            <p className="mt-1 font-semibold text-slate-900">
                              Available in report
                            </p>

                          </div>

                        </div>


                        {/* FOOTER */}

                        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">

                          <div className="flex items-center gap-2 text-xs text-slate-500">

                            <CalendarDays
                              size={14}
                            />

                            {formatDate(
                              scan.created_at
                            )}

                            {scan.image_filename && (
                              <>
                                <span>·</span>

                                <span className="max-w-[220px] truncate">
                                  {
                                    scan.image_filename
                                  }
                                </span>
                              </>
                            )}

                          </div>


                          <div
                            className={`flex items-center gap-2 text-xs ${
                              isOutlier
                                ? 'text-amber-700'
                                : analysisComplete
                                  ? 'text-emerald-700'
                                  : 'text-slate-500'
                            }`}
                          >

                            {isOutlier ? (
                              <AlertTriangle
                                size={14}
                              />
                            ) : (
                              <CheckCircle2
                                size={14}
                              />
                            )}

                            {isOutlier
                              ? 'Review recommended'
                              : analysisComplete
                                ? 'Analysis completed'
                                : 'Analysis pending'}

                          </div>

                        </div>

                      </div>
                    );
                  }
                )}

              </div>

            )}

          </div>

        </Card>

      )}

    </div>
  );
}


export default PatientsPage;