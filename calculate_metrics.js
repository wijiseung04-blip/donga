/* 수집된 데이터를 바탕으로 cycle time 계산 */
const issues = data.repository.issues.nodes;

// 각 이슈 별로 사이클 타임 계산
const cycleTime = issues.map(issue => {
  const created = new Date(issue.createdAt);
  const closed = new Date(issue.closedAt);

  // 밀리초 -> 일 단위 변환
  return (closed - created) / (1000 * 60 * 60 * 24);
});

// 전체 평균 Cycle Time 도출
const avgCycleTime = cycleTime.reduce((a, b) => a + b) / cycleTime.length;

console.log(`Average Cycle Time: ${avgCycleTime.toFixed(1)} days`);
