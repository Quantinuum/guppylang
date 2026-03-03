(module
  ;; --- Function: Return two ---
  (func $two (result i64)
    i64.const 2)

  ;; --- Function: Add two i64s ---
  (func $add (param $a i64) (param $b i64) (result i64)
    (i64.add (local.get $a) (local.get $b))
  )

  ;; --- Function: Identity on floats ---
  (func $fid (param $a f64) (result f64)
    (local.get $a))

  ;; --- Function: Consume a float ---
  (func $eat_float (param $a f64))

  ;; Function with no inputs or outputs
  (func $nothing)


  ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
  ;; Now, functions we don't expect to work ;;
  ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

  ;; Function with multiple outputs
  (func $multiple_outputs (result f64) (result f64)
    (f64.const 1.0) (f64.const 2.0))

  ;; Invalid param type
  (func $bad_input_type (param i32))

  ;; Invalid output type
  (func $bad_output_type (result f32)
    (f32.const 42.0))

  (memory $mem (data "not_a_fn"))

  ;; --- Exports ---
  (export "add" (func $add))
  (export "two" (func $two))
  (export "fid" (func $fid))
  (export "consume_float" (func $eat_float))
  (export "nothing" (func $nothing))
  (export "multiple_outputs" (func $multiple_outputs))
  (export "bad_input_type" (func $bad_input_type))
  (export "bad_output_type" (func $bad_output_type))
  (export "non_fn" (memory $mem))
)
