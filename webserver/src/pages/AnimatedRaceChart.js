// src/components/AnimatedRaceChart.js
import React, { useState, useEffect, useRef } from 'react';
import * as d3 from 'd3'; // Importa a biblioteca D3.js
import '../components/AnimatedRaceChart.css';


const AnimatedRaceChart = () => {
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const svgRef = useRef(null); // Ref para o elemento SVG
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [animationComplete, setAnimationComplete] = useState(false);
  const intervalRef = useRef(null); // Ref para o intervalo de animação

  const margin = { top: 30, right: 10, bottom: 10, left: 120 }; // Ajustado para rótulos longos
  const width = 800 - margin.left - margin.right;
  const height = 500 - margin.top - margin.bottom;
  const colorPalette = [
    "#E10600", // F1 Red (Ferrari)
    "#00D2BE", // F1 Green (Mercedes)
    "#0072BB", // F1 Blue (Red Bull)
    "#FF8700", // F1 Orange (McLaren)
    "#6CD3BF", // Alpine Blue
    "#2293D1", // AlphaTauri Blue
    "#C8D468", // Aston Martin Green
    "#B6B6B6", // Haas Grey
    "#FFC800", // Sauber Green/Yellow
    "#3671C6", // Williams Blue

    // Adicione mais cores para mais pilotos se necessário
    "#FF00FF", "#00FFFF", "#FFFF00", "#8A2BE2", "#A52A2A", "#DEB887", "#5F9EA0", "#7FFF00", "#D2691E", "#FF7F50",
    "#6495ED", "#DC143C", "#006400", "#BDB76B", "#8B008B", "#FF1493", "#00BFFF", "#696969", "#1E90FF", "#B22222",
    "#FFFAF0", "#228B22", "#FF00FF", "#DCDCDC", "#F8F8FF", "#FFD700", "#DAA520", "#808080", "#008000", "#ADFF2F"
  ];

  // Crie a escala de cores ordinal (mapeia driverRef para uma cor)
  const colorScale = d3.scaleOrdinal(colorPalette);


  // 1. Fetching data from API
  useEffect(() => {
    const fetchRaceData = async () => {
      try {
        const response = await fetch('/api/animated_race_data/');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        // Filtrar dados para remover pilotos sem vitórias no primeiro frame
        // E garantir que todos os drivers tenham um nome, mesmo que não tenham vitórias
        const processedData = data.map(frame => ({
          ...frame,
          drivers: frame.drivers.filter(d => d.wins > 0) // Remover pilotos com 0 vitórias no início
        }));
        setChartData(processedData);
        setLoading(false);
      } catch (err) {
        console.error("Erro ao buscar dados da API de corrida:", err);
        setError("Não foi possível carregar os dados do gráfico de corrida.");
        setLoading(false);
      }
    };

    fetchRaceData();
  }, []);

  // 2. D3.js Rendering and Animation Logic
  useEffect(() => {
    if (!loading && chartData.length > 0) {
      const svg = d3.select(svgRef.current)
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .attr("viewBox", [0, 0, width + margin.left + margin.right, height + margin.top + margin.bottom]) // Para responsividade
        .attr("preserveAspectRatio", "xMidYMid meet");

      // Limpa o SVG antes de redesenhar
      svg.selectAll("*").remove();

      const g = svg.append("g")
        .attr("transform", `translate(<span class="math-inline">\{margin\.left\},</span>{margin.top})`);

      // Scales
      const xScale = d3.scaleLinear()
        .range([0, width]);

      const yScale = d3.scaleBand()
        .range([height, 0])
        .padding(0.1);

      // Eixos
      const xAxis = g => g.attr("transform", `translate(0,${height})`).call(d3.axisBottom(xScale));
      const yAxis = g => g.call(d3.axisLeft(yScale).tickSize(0).tickPadding(6));

      let bars = g.selectAll(".bar");
      let labels = g.selectAll(".label");
      let names = g.selectAll(".name");

      // Função para atualizar o gráfico para um dado frame
      const updateChart = (frame) => {
        if (!frame) return;

        const drivers = frame.drivers.slice(0, 20); // Limitar ao top 15 para visualização
        drivers.reverse(); // Para que o maior esteja no topo

        xScale.domain([0, d3.max(drivers, d => d.wins) * 1.1]); // Ajusta o domínio do X para um pouco mais que o máximo
        yScale.domain(drivers.map(d => d.driverName));

        g.select(".x-axis").remove(); // Remove eixos antigos
        g.select(".y-axis").remove();

        g.append("g").attr("class", "x-axis").call(xAxis);
        g.append("g").attr("class", "y-axis").call(yAxis);

        // Transições para as barras
        bars = g.selectAll(".bar")
          .data(drivers, d => d.driverRef);

        bars.enter()
          .append("rect")
          .attr("class", "bar")
          .attr("x", 0)
          .attr("y", d => yScale(d.driverName))
          .attr("height", yScale.bandwidth())
          .attr("width", d => xScale(d.wins))
          .attr("fill", d => colorScale(d.driverRef))
          .merge(bars)
          .transition()
          .duration(500) // Duração da transição entre as barras
          .ease(d3.easeLinear)
          .attr("x", 0)
          .attr("y", d => yScale(d.driverName))
          .attr("height", yScale.bandwidth())
          .attr("width", d => xScale(d.wins));

        bars.exit().remove();

        // Transições para os rótulos (vitórias)
        labels = g.selectAll(".label")
          .data(drivers, d => d.driverRef);

        labels.enter()
          .append("text")
          .attr("class", "label")
          .attr("x", d => xScale(d.wins) + 5) // Posição do texto
          .attr("y", d => yScale(d.driverName) + yScale.bandwidth() / 2 + 5)
          .text(d => d.wins)
          .merge(labels)
          .transition()
          .duration(500)
          .ease(d3.easeLinear)
          .attr("x", d => xScale(d.wins) + 5)
          .attr("y", d => yScale(d.driverName) + yScale.bandwidth() / 2 + 5)
          .text(d => d.wins);

        labels.exit().remove();

        // Atualiza Race Info
        //raceInfoText.text(frame.raceInfo || frame.timeStep).transition().duration(500);
      };

      // Inicia a animação
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      setCurrentFrameIndex(0); // Reinicia a animação ao carregar novos dados
      setAnimationComplete(false); // <-- Resetar ao iniciar nova animação
      intervalRef.current = setInterval(() => {
        setCurrentFrameIndex(prevIndex => {
          const nextIndex = prevIndex + 1;
          if (nextIndex < chartData.length) {
            updateChart(chartData[nextIndex]);
            return nextIndex;
          } else {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
            setAnimationComplete(true);
            console.log("Animação finalizada no último frame.");
            return prevIndex;
          }
        });
      }, 75); // Intervalo de 1 segundo por frame (ajuste para mais rápido/lento)

      // Limpeza ao desmontar o componente
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };
    }
  }, [loading, chartData, width, height]); // Adicione width/height para re-renderizar em redimensionamento (básico)


  if (loading) {
    return <div className="chart-loading">Carregando dados do gráfico...</div>;
  }

  if (error) {
    return <div className="chart-error" style={{ color: 'red' }}>{error}</div>;
  }

  // Estrutura básica para o gráfico (um SVG, por exemplo)
  return (
    <div className="animated-race-chart-container">
      <h2 className="widget-title">Histórico de Vitórias de Pilotos</h2> {/* Título dinâmico */}
      <svg ref={svgRef} className="animated-chart"></svg>

      {/* ESTE É O LUGAR EXATO PARA O FEEDBACK VISUAL: LOGO ABAIXO DO SVG */}
      {animationComplete && (
        <div className="animation-complete-message" style={{ color: '#00D2BE', marginTop: '10px', fontSize: '1.2em', fontWeight: 'bold' }}>
          Animação Concluída!
        </div>
      )}

      <div className="chart-info">
        {/* Informações adicionais podem vir aqui, como o frame atual/raceInfo */}
        <p>Total de Frames Carregados: {chartData.length}</p>
      </div>
    </div>
  );
};

export default AnimatedRaceChart;