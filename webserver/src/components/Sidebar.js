// src/components/Sidebar.js
import { Link } from 'react-router-dom'; // <-- IMPORTE ESTA LINHA
import './Sidebar.css';

const Sidebar = () => {
  return (
    <aside className="sidebar">
      <nav>
        <ul>
          {/* Para a página inicial, use "/" */}
          <li><Link to="/">Início</Link></li>
          <li><Link to="/latest-results">Resultados</Link></li>
          <li><Link to="/championship-standings">Classificação</Link></li>
          <li><Link to="/driver-profiles">Pilotos</Link></li>
          <li><Link to="/team-profiles">Equipes</Link></li>
          <li><Link to="/track-guide">Autódromos</Link></li>
          {/* ESTA É A LINHA CRÍTICA PARA O GRÁFICO ANIMADO */}
          <li><Link to="/historical-stats">Estatísticas Históricas</Link></li>
        </ul>
      </nav>
      {/* Pode adicionar filtros ou links rápidos aqui */}
    </aside>
  );
};

export default Sidebar;