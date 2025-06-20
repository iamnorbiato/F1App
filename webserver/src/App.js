// src/App.js
import React from 'react'; // Este React continua aqui para ser o primeiro componente
import { Routes, Route } from 'react-router-dom'; // IMPORTE ESTAS LINHAS
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import MainDashboardContent from './pages/MainDashboardContent'; // NOVO COMPONENTE DE PÁGINA
import AnimatedRaceChartPage from './pages/AnimatedRaceChart'; // SEU GRÁFICO AGORA É UMA PÁGINA
import './App.css';
import './index.css';

function App() {
  return (
    <div className="App">
      <Header />
      <main className="main-content">
        <Sidebar />
        <Routes> {/* AS ROTAS SERÃO DEFINIDAS AQUI */}
          <Route path="/" element={<MainDashboardContent />} /> {/* Rota para a página principal */}
          <Route path="/historical-stats" element={<AnimatedRaceChartPage />} /> {/* Rota para a página do gráfico */}
          {/* Você pode adicionar mais rotas aqui, ex: /teams, /drivers */}
        </Routes>
      </main>
    </div>
  );
}

export default App;