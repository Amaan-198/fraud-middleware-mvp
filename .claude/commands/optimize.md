# Optimize Command

Profile and optimize slow code paths.

## Steps

1. Profile current performance
2. Identify bottlenecks
3. Suggest optimizations
4. Implement if <30 lines
5. Re-test performance

## Common Optimizations

- Cache feature computations
- Batch database queries
- Use ONNX Runtime optimizations
- Simplify feature engineering
- Remove unnecessary validations in hot path

## Target Metrics

- P95: <60ms
- P99: <90ms
- Memory: <500MB
- Throughput: >100 TPS
