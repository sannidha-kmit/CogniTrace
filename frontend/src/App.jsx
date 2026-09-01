import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

import Login from './pages/Login';
import StudentRegister from './pages/StudentRegister';
import TeacherRegister from './pages/TeacherRegister';

import StudentDashboard from './pages/StudentDashboard';
import StudentTeacherCourses from './pages/StudentTeacherCourses';
import StudentCourseDetails from './pages/StudentCourseDetails';
import StudentWatchVideo from './pages/StudentWatchVideo';

import TeacherDashboard from './pages/TeacherDashboard';
import AddCourse from './pages/AddCourse';
import TeacherCourseList from './pages/TeacherCourseList';
import TeacherStudentList from './pages/TeacherStudentList';
import TeacherTranscriptView from './pages/TeacherTranscriptView';
import TeacherConceptView from './pages/TeacherConceptView';
import TeacherStudentDatasetView from './pages/TeacherStudentDatasetView';
import TeacherDatasetManagement from './pages/TeacherDatasetManagement';
import TeacherDatasetDetail from './pages/TeacherDatasetDetail';

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public Authentication Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register/student" element={<StudentRegister />} />
        <Route path="/register/teacher" element={<TeacherRegister />} />

        {/* Protected Student Routes */}
        <Route 
          path="/student/dashboard" 
          element={
            <ProtectedRoute requiredRole="student">
              <StudentDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/student/home" 
          element={<Navigate to="/student/dashboard" replace />} 
        />
        <Route 
          path="/student/teacher/:teacherId" 
          element={
            <ProtectedRoute requiredRole="student">
              <StudentTeacherCourses />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/student/course/:courseId" 
          element={
            <ProtectedRoute requiredRole="student">
              <StudentCourseDetails />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/student/course/:courseId/watch" 
          element={
            <ProtectedRoute requiredRole="student">
              <StudentWatchVideo />
            </ProtectedRoute>
          } 
        />

        {/* Protected Teacher Routes */}
        <Route 
          path="/teacher/dashboard" 
          element={
            <ProtectedRoute requiredRole="teacher">
              <TeacherDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/teacher/home" 
          element={<Navigate to="/teacher/dashboard" replace />} 
        />
        <Route 
          path="/teacher/courses/add" 
          element={
            <ProtectedRoute requiredRole="teacher">
              <AddCourse />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/teacher/courses" 
          element={
            <ProtectedRoute requiredRole="teacher">
              <TeacherCourseList />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/teacher/courses/:courseId/transcript" 
          element={
            <ProtectedRoute requiredRole="teacher">
              <TeacherTranscriptView />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/teacher/courses/:courseId/concepts" 
          element={
            <ProtectedRoute requiredRole="teacher">
              <TeacherConceptView />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/teacher/students" 
          element={
            <ProtectedRoute requiredRole="teacher">
              <TeacherStudentList />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/teacher/students/:rollNumber" 
          element={
            <ProtectedRoute requiredRole="teacher">
              <TeacherStudentDatasetView />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/teacher/datasets" 
          element={
            <ProtectedRoute requiredRole="teacher">
              <TeacherDatasetManagement />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/teacher/datasets/:datasetType" 
          element={
            <ProtectedRoute requiredRole="teacher">
              <TeacherDatasetDetail />
            </ProtectedRoute>
          } 
        />

        {/* Default Fallback */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </AuthProvider>
  );
}
