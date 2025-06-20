// src/pages/MainDashboardContent.js
import React, { useState } from 'react';
import DashboardWidget from '../components/DashboardWidget';
import './MainDashboardContent.css'; // Crie este CSS depois

const MainDashboardContent = () => {
  // Exemplo de dados mockados (copiados do seu App.js anterior)
  const [latestNews, setLatestNews] = useState([
    { id: 1, title: "Verstappen vence GP de Mônaco em corrida estratégica", summary: "Max Verstappen garantiu mais uma vitória crucial...", imageUrl: "https://via.placeholder.com/300x200?text=Noticia1" },
    { id: 2, title: "Mercedes anuncia atualizações importantes para o carro", summary: "Lewis Hamilton e George Russell esperam por melhorias...", imageUrl: "https://via.placeholder.com/300x200?text=Noticia2" },
    { id: 3, title: "Ferrari otimista após desempenho no simulador", summary: "Carlos Sainz e Charles Leclerc confiantes para a próxima etapa...", imageUrl: "https://via.placeholder.com/300x200?text=Noticia3" },
  ]);

  const [nextRace, setNextRace] = useState({
    name: "Grande Prêmio do Canadá",
    date: "2025-06-22",
    track: "Circuit Gilles Villeneuve",
    countdown: "5 dias, 10h, 30min"
  });

  const [topDrivers, setTopDrivers] = useState([
    { id: 1, name: "Max Verstappen", team: "Red Bull", points: 150, photo: "https://via.placeholder.com/50x50?text=MV" },
    { id: 2, name: "Sergio Perez", team: "Red Bull", points: 120, photo: "https://via.placeholder.com/50x50?text=SP" },
    { id: 3, name: "Charles Leclerc", team: "Ferrari", points: 100, photo: "https://via.placeholder.com/50x50?text=CL" },
    { id: 4, name: "Lewis Hamilton", team: "Mercedes", points: 90, photo: "https://via.placeholder.com/50x50?text=LH" },
  ]);

  return (
    <section className="dashboard-grid">
      <DashboardWidget title="Destaques e Notícias Recentes">
        <div className="news-grid">
          {latestNews.map(news => (
            <div key={news.id} className="news-card">
              <img src={news.imageUrl} alt={news.title} />
              <h3>{news.title}</h3>
              <p>{news.summary}</p>
            </div>
          ))}
        </div>
      </DashboardWidget>

      <DashboardWidget title="Próxima Corrida">
        <div className="next-race-info">
          <h4>{nextRace.name}</h4>
          <p>Data: {nextRace.date}</p>
          <p>Autódromo: {nextRace.track}</p>
          <p>Contagem Regressiva: <span style={{color: '#00D2BE', fontWeight: 'bold'}}>{nextRace.countdown}</span></p>
        </div>
      </DashboardWidget>

      <DashboardWidget title="Classificação de Pilotos (Top 4)">
        <ul className="driver-standings">
          {topDrivers.map(driver => (
            <li key={driver.id}>
              <img src={driver.photo} alt={driver.name} className="driver-photo-small" />
              <span>{driver.name} ({driver.team}) - </span>
              <span style={{color: '#FF8700', fontWeight: 'bold'}}>{driver.points} pts</span>
            </li>
          ))}
        </ul>
      </DashboardWidget>

      {/* NOVO PLACEHOLDER AQUI */}
      <DashboardWidget title="Outras Informações (Placeholder)">
        <p>Este espaço pode ser usado para um gráfico rápido, um placar ao vivo, ou outros destaques na página principal.</p>
        <p style={{color: '#00D2BE'}}>Conteúdo dinâmico virá aqui!</p>
      </DashboardWidget>

      {/* Pode adicionar mais widgets aqui */}
    </section>
  );
};

export default MainDashboardContent;