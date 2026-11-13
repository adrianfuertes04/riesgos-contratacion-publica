// Consultas Cypher de ejemplo (fase 0, semanas 10-12 del plan).

// 1. Red de un organismo: empresas adjudicatarias con importe total.
MATCH (o:Organismo {id: $organismo})-[:CONVOCA]->(:Licitacion)-[:TIENE_LOTE*0..1]->(x)<-[a:ADJUDICATARIA]-(e:Empresa)
RETURN e.nombre_normalizado AS empresa, count(a) AS contratos, sum(a.importe) AS importe
ORDER BY importe DESC LIMIT 25;

// 2. Empresas que ganan en muchos organismos distintos.
MATCH (o:Organismo)-[:CONVOCA]->(:Licitacion)-[:TIENE_LOTE*0..1]->(x)<-[:ADJUDICATARIA]-(e:Empresa)
RETURN e.id AS empresa, e.nombre_normalizado AS nombre, count(DISTINCT o) AS organismos
ORDER BY organismos DESC LIMIT 25;

// 3. Adjudicaciones con un único licitador en un organismo.
MATCH (o:Organismo {id: $organismo})-[:CONVOCA]->(l:Licitacion)-[:TIENE_LOTE*0..1]->(x)<-[a:ADJUDICATARIA]-(e:Empresa)
WHERE a.n_licitadores = 1
RETURN l.objeto, e.nombre_normalizado, a.importe, a.fecha ORDER BY a.fecha DESC;

// 4. Proyección para Graph Data Science (indicador 9, fase 3): grafo bipartito organismo-empresa.
MATCH (o:Organismo)-[:CONVOCA]->(:Licitacion)-[:TIENE_LOTE*0..1]->(x)<-[a:ADJUDICATARIA]-(e:Empresa)
WITH o, e, sum(a.importe) AS importe
WITH gds.graph.project('organismo_empresa', o, e, {relationshipProperties: {importe: importe}}) AS g
RETURN g.graphName, g.nodeCount, g.relationshipCount;
// CALL gds.pageRank.stream('organismo_empresa') YIELD nodeId, score ...
// CALL gds.louvain.stream('organismo_empresa') YIELD nodeId, communityId ...
